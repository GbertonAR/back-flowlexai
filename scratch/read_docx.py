import docx

def read_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

if __name__ == "__main__":
    path = r"C:\GBerton2026\Documentos\FlowLexAI\Mejora a RAG de FlowLexAI.docx"
    try:
        text = read_docx(path)
        with open("scratch/docx_content.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("Success: content saved to scratch/docx_content.txt")
    except Exception as e:
        print(f"Error: {e}")
