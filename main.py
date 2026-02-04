import streamlit as st
import random
import re
from pypdf import PdfReader

# --- 1. PARSAREA PDF-ULUI (CU FIX PENTRU "10.000") ---
def parse_pdf_quiz(file_path):
    """
    Citește PDF-ul și extrage întrebările și răspunsurile.
    Include fix-ul pentru numerele mari (ex: 10.000 lei nu e întrebarea 10).
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"Eroare la citirea PDF: {e}")
        return []

    lines = text.split('\n')
    questions = []
    current_q = None
    
    # --- AICI E SCHIMBAREA CHEIE ---
    # (?!\d) înseamnă: "Caută un număr și punct (ex: 3.), 
    # DAR asigură-te că după punct NU urmează altă cifră".
    # Asta previne ca "10.000" să fie luat drept întrebarea "10."
    q_pattern = re.compile(r'^(\d+)\.(?!\d)\s*(.+)')
    
    # Pattern pentru opțiuni (a), b), etc.)
    opt_pattern = re.compile(r'^([a-zA-Z])\)\s*(.+)')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        q_match = q_pattern.match(line)
        if q_match:
            # Salvăm întrebarea anterioară dacă există
            if current_q:
                questions.append(current_q)
            
            # Începem întrebare nouă
            current_q = {
                "id": q_match.group(1),
                "text": q_match.group(2),
                "options": [],
                "correct_indices": []
            }
        elif current_q:
            # Verificăm dacă e opțiune de răspuns (a, b, c...)
            opt_match = opt_pattern.match(line)
            if opt_match:
                opt_text = opt_match.group(2)
                # Verificăm marcajul ` pentru răspuns corect
                is_correct = '@' in opt_text or '@' in line
                clean_text = opt_text.replace('@', '').strip()
                
                current_q["options"].append(clean_text)
                if is_correct:
                    current_q["correct_indices"].append(len(current_q["options"]) - 1)
            else:
                # E o continuare a textului (ori la întrebare, ori la ultima opțiune)
                if current_q["options"]:
                    current_q["options"][-1] += " " + line.replace('@', '')
                else:
                    current_q["text"] += " " + line

    # Adăugăm ultima întrebare rămasă în memorie
    if current_q:
        questions.append(current_q)
        
    return questions

# --- 2. FUNCȚII AUXILIARE ---
def restart_quiz():
    """Resetează totul."""
    st.session_state.session_id += 1
    st.session_state.verified_questions = set()
    st.session_state.correct_answers = set()
    if 'questions' in st.session_state:
        random.shuffle(st.session_state.questions)

# --- 3. INTERFAȚA PRINCIPALĂ ---
def main():
    st.set_page_config(page_title="Quiz Conta", page_icon="📝", layout="wide")
    
    # Titlu principal
    st.title("📝 Test Grilă Conta")

    # Inițializări Session State
    if 'questions' not in st.session_state:
        # Încearcă să citești fișierul. Asigură-te că test_TIA.pdf e lângă script.
        raw_questions = parse_pdf_quiz("Grila_buna_MATE.pdf")
        if raw_questions:
            random.shuffle(raw_questions)
            st.session_state.questions = raw_questions
        else:
            st.warning("Nu s-au găsit întrebări sau fișierul PDF lipsește.")
            st.stop()
            
    if 'session_id' not in st.session_state:
        st.session_state.session_id = 0
    if 'verified_questions' not in st.session_state:
        st.session_state.verified_questions = set()
    if 'correct_answers' not in st.session_state:
        st.session_state.correct_answers = set()

    sid = st.session_state.session_id
    total_questions = len(st.session_state.questions)
    verified_count = len(st.session_state.verified_questions)
    current_score = len(st.session_state.correct_answers)

    # --- SIDEBAR (STATISTICI LIVE) ---
    with st.sidebar:
        st.header("📊 Progres")
        if total_questions > 0:
            progres = verified_count / total_questions
            st.progress(progres)
            st.write(f"Întrebări completate: **{verified_count} / {total_questions}**")
            st.write(f"Răspunsuri corecte: **{current_score}**")
            
            if verified_count > 0:
                acc = (current_score / verified_count) * 100
                st.metric("Acuratețe momentană", f"{acc:.1f}%")
        
        st.markdown("---")
        st.button("🔄 Restart Test", on_click=restart_quiz)

    # --- AFIȘAREA LISTEI DE ÎNTREBĂRI ---
    for i, q in enumerate(st.session_state.questions):
        
        # Container vizual pentru fiecare întrebare
        with st.container():
            st.markdown(f"#### {i+1}. {q['text']}")
            
            selected_indices = []
            
            # Afișăm opțiunile
            for idx, opt in enumerate(q['options']):
                chk_key = f"chk_{sid}_{i}_{idx}"
                # Dezactivăm bifarea după ce ai verificat întrebarea
                is_disabled = i in st.session_state.verified_questions
                
                checked = st.checkbox(opt, key=chk_key, disabled=is_disabled)
                if checked:
                    selected_indices.append(idx)

            # --- BUTONUL DE VERIFICARE ---
            if i not in st.session_state.verified_questions:
                if st.button(f"Verifică", key=f"btn_check_{sid}_{i}"):
                    st.session_state.verified_questions.add(i)
                    
                    # Calculăm dacă e corect DOAR dacă există răspuns marcat în PDF
                    if q['correct_indices']:
                        if sorted(selected_indices) == sorted(q['correct_indices']):
                            st.session_state.correct_answers.add(i)
                    
                    st.rerun()
            
            # --- AFIȘAREA REZULTATULUI IMEDIAT (după click) ---
            if i in st.session_state.verified_questions:
                correct_indices = q['correct_indices']
                
                if not correct_indices:
                    st.warning("⚠️ Această întrebare nu are răspunsul marcat în PDF.")
                else:
                    if sorted(selected_indices) == sorted(correct_indices):
                        st.success("✅ Corect!")
                    else:
                        correct_texts = [q['options'][idx] for idx in correct_indices]
                        st.error("❌ Greșit.")
                        st.info(f"**Răspuns corect:** {', '.join(correct_texts)}")
            
            st.markdown("---")

    # --- ZONA DE SCOR FINAL (Apare jos când termini tot) ---
    if verified_count == total_questions and total_questions > 0:
        
        # Recalculăm întrebările care chiar aveau răspuns (să nu penalizăm erorile de PDF)
        valid_total = sum(1 for q in st.session_state.questions if q['correct_indices'])
        
        if valid_total > 0:
            final_percentage = (current_score / valid_total) * 100
        else:
            final_percentage = 0

        st.markdown("""
        <div style="background-color:#d4edda;padding:20px;border-radius:10px;border:2px solid #c3e6cb">
            <h2 style="color:#155724;text-align:center;">🏆 TEST COMPLETAT!</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Scor Final", f"{current_score} / {valid_total}")
        col2.metric("Procentaj", f"{final_percentage:.2f}%")
        
        if final_percentage >= 50:
            st.balloons()
            col3.success("AI PROMOVAT!")
        else:
            col3.error("MAI ÎNCEARCĂ...")

if __name__ == "__main__":
    main()
