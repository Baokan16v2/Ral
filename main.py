import streamlit as st
import random
import re
from pypdf import PdfReader

def parse_pdf_quiz(file_path):
    """
    Citește PDF-ul și extrage întrebările și răspunsurile.
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
    
    q_pattern = re.compile(r'^(\d+)\.\s*(.+)')
    opt_pattern = re.compile(r'^([a-zA-Z])\)\s*(.+)')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        q_match = q_pattern.match(line)
        if q_match:
            if current_q:
                questions.append(current_q)
            current_q = {
                "id": q_match.group(1),
                "text": q_match.group(2),
                "options": [],
                "correct_indices": []
            }
        elif current_q:
            opt_match = opt_pattern.match(line)
            if opt_match:
                opt_text = opt_match.group(2)
                # Verificăm marcajul `
                is_correct = '`' in opt_text or '`' in line
                clean_text = opt_text.replace('`', '').strip()
                
                current_q["options"].append(clean_text)
                if is_correct:
                    current_q["correct_indices"].append(len(current_q["options"]) - 1)
            else:
                if current_q["options"]:
                    current_q["options"][-1] += " " + line.replace('`', '')
                else:
                    current_q["text"] += " " + line

    if current_q:
        questions.append(current_q)
        
    return questions

def restart_quiz():
    """Resetează testul, amestecă întrebările și șterge istoricul verificărilor."""
    st.session_state.session_id += 1
    st.session_state.verified_questions = set() # Resetăm întrebările verificate
    st.session_state.correct_answers = set()    # Resetăm contorul de răspunsuri corecte
    if 'questions' in st.session_state:
        random.shuffle(st.session_state.questions)

def main():
    st.set_page_config(page_title="Quiz (nush cum se cheama materia)", page_icon="📝")
    st.title("📝 Test(nush cum se cheama materia)")

    # --- INIȚIALIZĂRI ---
    if 'questions' not in st.session_state:
        # Asigură-te că fișierul test_TIA.pdf există în același folder
        raw_questions = parse_pdf_quiz("Grile_v2_corectate.pdf")
        if raw_questions:
            random.shuffle(raw_questions)
            st.session_state.questions = raw_questions
        else:
            st.warning("Nu s-au găsit întrebări în PDF sau fișierul lipsește.")
            st.stop()
            
    if 'session_id' not in st.session_state:
        st.session_state.session_id = 0
        
    # Ținem minte care întrebări au fost deja verificate
    if 'verified_questions' not in st.session_state:
        st.session_state.verified_questions = set()

    # Ținem minte indexul întrebărilor la care s-a răspuns corect (pentru scor)
    if 'correct_answers' not in st.session_state:
        st.session_state.correct_answers = set()

    sid = st.session_state.session_id

    # --- AFIȘAREA ÎNTREBĂRILOR ---
    
    # Iterăm prin întrebări
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"##### {i+1}. {q['text']}")
        
        selected_indices = []
        
        # Afișăm opțiunile
        for idx, opt in enumerate(q['options']):
            chk_key = f"chk_{sid}_{i}_{idx}"
            is_disabled = i in st.session_state.verified_questions
            
            checked = st.checkbox(opt, key=chk_key, disabled=is_disabled)
            if checked:
                selected_indices.append(idx)

        # Butonul de verificare per întrebare
        if i not in st.session_state.verified_questions:
            if st.button(f"Verifică întrebarea {i+1}", key=f"btn_check_{sid}_{i}"):
                st.session_state.verified_questions.add(i)
                
                # Logică de punctaj:
                # Doar dacă întrebarea are un răspuns marcat în PDF (q['correct_indices'] nu e gol)
                if q['correct_indices']:
                    if sorted(selected_indices) == sorted(q['correct_indices']):
                        st.session_state.correct_answers.add(i)
                
                st.rerun()
        
        # --- AFIȘARE REZULTAT (Dacă a fost verificată) ---
        if i in st.session_state.verified_questions:
            correct_indices = q['correct_indices']
            
            # CAZ 1: Nu există răspuns marcat în PDF (nu s-a găsit `)
            if not correct_indices:
                st.warning("⚠️ Nu se știe care e răspunsul corect la această grilă (nu a fost marcat în PDF).")
            
            # CAZ 2: Există răspuns, verificăm dacă utilizatorul a răspuns corect
            else:
                if sorted(selected_indices) == sorted(correct_indices):
                    st.success("✅ Corect!")
                else:
                    correct_texts = [q['options'][idx] for idx in correct_indices]
                    st.error("❌ Greșit.")
                    st.markdown(f"**Răspunsul corect era:** {', '.join(correct_texts)}")

        st.markdown("---")

    # --- ZONA DE SCOR FINAL ---
    total_questions = len(st.session_state.questions)
    verified_count = len(st.session_state.verified_questions)

    # Afișăm scorul doar dacă s-a răspuns la toate întrebările (sau măcar la una)
    if verified_count == total_questions and total_questions > 0:
        
        # Calculăm numărul de întrebări valide (care aveau răspuns în PDF)
        valid_questions_count = sum(1 for q in st.session_state.questions if q['correct_indices'])
        
        user_score = len(st.session_state.correct_answers)
        
        if valid_questions_count > 0:
            percentage = (user_score / valid_questions_count) * 100
        else:
            percentage = 0.0

        st.markdown("### 🏆 Rezultate Finale")
        st.info(f"Ai răspuns la toate întrebările!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Răspunsuri Corecte", value=f"{user_score} / {valid_questions_count}")
        with col2:
            st.metric(label="Procentaj", value=f"{percentage:.2f}%")

        if percentage >= 50:
            st.balloons()
        
        # Avertisment dacă au existat întrebări fără răspuns în PDF
        invalid_count = total_questions - valid_questions_count
        if invalid_count > 0:
            st.caption(f"*Notă: {invalid_count} întrebări nu au avut un răspuns marcat în PDF și au fost excluse din calculul procentajului.*")

    # Buton global de resetare
    st.button("🔄 Reia Testul de la zero", on_click=restart_quiz)

if __name__ == "__main__":
    main()
