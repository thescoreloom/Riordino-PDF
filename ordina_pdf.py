import os
import re
import sys
from collections import Counter
from pypdf import PdfWriter

CATEGORY_RULES = [
    # 0. Partitura (in cima)
    {
        "cat_idx": 0,
        "name": "Partitura",
        "rules": [
            (1, "Partitura / Score", [
                r"\b(partitura|full\s*score|score|conductor|conduttore|direzione|partitur)\b"
            ])
        ]
    },
    # 1. Voci
    {
        "cat_idx": 1,
        "name": "Voci",
        "rules": [
            (1, "Voce Solista", [r"\b(voice|solo\s*voice|voce|voci|vocal|vocals|canto|cantante|solista)\b"]),
            (2, "Coro", [r"\b(choir|chorus|coro|satb)\b"])
        ]
    },
    # 2. Flauti
    {
        "cat_idx": 2,
        "name": "Flauti",
        "rules": [
            (1, "Ottavino / Piccolo", [r"\b(piccolo|ottavino)\b"]),
            (2, "Flauto", [r"\b(flute|flauto|flauti|alto\s*flute|bass\s*flute)\b"])
        ]
    },
    # 3. Ance doppie (oboe e fagotto)
    {
        "cat_idx": 3,
        "name": "Ance doppie",
        "rules": [
            (1, "Oboe / Corno Inglese", [r"\b(oboe|oboes|english\s*horn|cor\s*anglais|corno\s*inglese)\b"]),
            (2, "Fagotto / Controfagotto", [r"\b(bassoon|fagotto|fagotti|contrabassoon|controfagotto)\b"])
        ]
    },
    # 4. Clarinetti (mib, poi i sib, poi il basso)
    {
        "cat_idx": 4,
        "name": "Clarinetti",
        "rules": [
            (1, "Clarinetto Mib", [
                r"\b(clarinet.*(eb|mib)|(eb|mib).*clarinet)\b",
                r"\b(piccolo\s*clarinet|clarinetto\s*piccolo)\b"
            ]),
            (2, "Clarinetto Sib / Standard", [
                r"\b(clarinet.*(bb|sib)|(bb|sib).*clarinet)\b",
                r"\b(clarinet|clarinetto|clarinetti)\b"
            ]),
            (3, "Clarinetto Basso", [
                r"\b(bass.*clarinet|clarinetto.*basso|contrabass.*clarinet|contra-alto.*clarinet)\b"
            ])
        ]
    },
    # 5. Sax (soprano alto tenore baritono, basso se c'è)
    {
        "cat_idx": 5,
        "name": "Sassofoni",
        "rules": [
            (1, "Sax Soprano", [r"\b(soprano\s*sax|sax\s*soprano|sopranino\s*sax|soprano\s*saxophone)\b"]),
            (2, "Sax Alto", [r"\b(alto\s*sax|sax\s*alto|contralto\s*sax|sax\s*contralto|alto\s*saxophone)\b"]),
            (3, "Sax Tenore", [r"\b(tenor\s*sax|sax\s*tenore|tenor\s*saxophone)\b"]),
            (4, "Sax Baritono", [r"\b(baritone\s*sax|sax\s*baritono|bari\s*sax|baritone\s*saxophone)\b"]),
            (5, "Sax Basso", [r"\b(bass\s*sax|sax\s*basso|bass\s*saxophone)\b"]),
            (6, "Sax Generico", [r"\b(sax|saxophone|sassofono)\b"])
        ]
    },
    # 6. Corni
    {
        "cat_idx": 6,
        "name": "Corni",
        "rules": [
            (1, "Corno in Fa / Horn", [r"\b(horn\s*in\s*f|f\s*horn|french\s*horn|corno\s*in\s*fa|horn|horns|corno|corni)\b"])
        ]
    },
    # 7. Trombe
    {
        "cat_idx": 7,
        "name": "Trombe",
        "rules": [
            (1, "Tromba / Cornetta / Flicorno", [
                r"\b(trumpet|trumpets|tromba|trombe|cornet|cornetta|cornette|flugelhorn|flügelhorn|flicorno\s*soprano)\b"
            ])
        ]
    },
    # 8. Tromboni (tenore/std poi basso)
    {
        "cat_idx": 8,
        "name": "Tromboni",
        "rules": [
            (1, "Trombone Tenore / Std", [r"\b(tenor\s*trombone|trombone|tromboni)\b"]),
            (2, "Trombone Basso", [r"\b(bass\s*trombone|trombone\s*basso)\b"])
        ]
    },
    # 9. Eufonio
    {
        "cat_idx": 9,
        "name": "Eufonio",
        "rules": [
            (1, "Eufonio / Flicorno Baritono", [
                r"\b(euphonium|eufonio|baritone\s*horn|baritone\s*b\.?c\.?|baritone\s*t\.?c\.?|flicorno\s*baritono|flicorno\s*tenore)\b"
            ])
        ]
    },
    # 10. Tuba
    {
        "cat_idx": 10,
        "name": "Tuba",
        "rules": [
            (1, "Tuba / Bassotuba", [r"\b(tuba|bass\s*tuba|bassotuba|sousaphone|bassi)\b"])
        ]
    },
    # 11. Corde pizzicate, chitarra, basso elettrico
    {
        "cat_idx": 11,
        "name": "Corde e Basso Elettrico",
        "rules": [
            (1, "Arpa", [r"\b(harp|arpa)\b"]),
            (2, "Chitarra", [r"\b(acoustic\s*guitar|electric\s*guitar|guitar|chitarra)\b"]),
            (3, "Basso Elettrico / Contrabbasso", [
                r"\b(electric\s*bass|basso\s*elettrico|bass\s*guitar|string\s*bass|double\s*bass|contrabbasso)\b"
            ])
        ]
    },
    # 12. Tastiere (pianoforte, organo, keyboard etc)
    {
        "cat_idx": 12,
        "name": "Tastiere",
        "rules": [
            (1, "Tastiere / Piano / Organo", [
                r"\b(piano|pianoforte|keyboard|tastiera|tastiere|organ|organo|synth|synthesizer|celesta|harpsichord|clavicembalo)\b"
            ])
        ]
    },
    # 13. Percussioni determinate (glockenspiel, mallet, vibrafoni vari e timpani)
    {
        "cat_idx": 13,
        "name": "Percussioni Determinate",
        "rules": [
            (1, "Mallet / Tastiere a percussione", [
                r"\b(glockenspiel|mallet|mallets|vibraphone|vibrafono|xylophone|xilofono|marimba|tubular\s*bells|campane\s*tubolari|chimes|crotales|campanelli)\b"
            ]),
            (2, "Timpani", [r"\b(timpani|timpany|kettledrums)\b"])
        ]
    },
    # 14. Percussioni indeterminate (batteria e percussioni, accessori etc..)
    {
        "cat_idx": 14,
        "name": "Percussioni Indeterminate",
        "rules": [
            (1, "Batteria", [r"\b(drum\s*set|drums|drum\s*kit|batteria)\b"]),
            (2, "Percussioni / Accessori", [
                r"\b(percussion|percussioni|accessories|accessori|snare|rullante|cymbals|piatti|grancassa|bass\s*drum|tambourine|tamburello|triangle|triangolo|congas|bongos|timbales|shaker|claves|castanets|wood\s*block|gong|tam-tam)\b"
            ])
        ]
    }
]


def natural_split(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]


def classify_instrument(filename, all_files=None):
    stem = re.sub(r'\.pdf$', '', filename, flags=re.I).strip()
    lower = stem.lower()

    # 0. Partitura / Score esplicita o file titolo (es. "Ballo Ballo 1.pdf" senza trattino/parte)
    if re.search(r'\b(partitura|full\s*score|score|conductor|conduttore|direzione|partitur)\b', lower):
        return (0, 1, "Partitura (In Cima)")

    if " - " not in filename:
        if all_files:
            is_base_title = any(
                f != filename and f.lower().startswith(lower + ' - ')
                for f in all_files
            )
            if is_base_title:
                return (0, 2, "Partitura (Titolo)")
        else:
            return (0, 2, "Partitura (Titolo)")

    # Risoluzione precedenze composte
    if re.search(r'\b(electric\s*bass|basso\s*elettrico|bass\s*guitar)\b', lower):
        return (11, 3, "Basso Elettrico")

    if re.search(r'\b(bass.*clarinet|clarinetto.*basso|contrabass.*clarinet)\b', lower):
        return (4, 3, "Clarinetto Basso")

    if re.search(r'\b(bass\s*trombone|trombone\s*basso)\b', lower):
        return (8, 2, "Trombone Basso")

    if re.search(r'\b(bassoon|fagotto|fagotti|contrabassoon|controfagotto)\b', lower):
        return (3, 2, "Fagotto")

    if re.search(r'\b(baritone\s*sax|sax\s*baritono|bari\s*sax)\b', lower):
        return (5, 4, "Sax Baritono")

    if re.search(r'\b(english\s*horn|corno\s*inglese|cor\s*anglais)\b', lower):
        return (3, 1, "Oboe / Corno Inglese")

    # Categorie da 1 a 14
    for cat in CATEGORY_RULES:
        if cat["cat_idx"] == 0:
            continue
        for sub_idx, sub_name, regex_list in cat["rules"]:
            for pattern in regex_list:
                if re.search(pattern, lower):
                    return (cat["cat_idx"], sub_idx, f"{cat['name']} ({sub_name})")

    # 15. Il resto in coda
    return (15, 0, "Altro / Coda")


def get_sort_key(filename, all_files=None):
    cat_idx, sub_idx, _ = classify_instrument(filename, all_files)
    return (cat_idx, sub_idx, natural_split(filename))


def detect_piece_title(file_list):
    # 1. Se esiste un file score senza trattino (es. Ballo Ballo 1.pdf)
    scores = [f for f in file_list if " - " not in f]
    if scores:
        return re.sub(r'\.pdf$', '', scores[0], flags=re.I).strip()

    # 2. Prefisso prima di ' - ' comune a più file
    prefixes = []
    for f in file_list:
        m = re.match(r'^(.*?)\s*-\s*', f)
        if m:
            prefixes.append(m.group(1).strip())
    if prefixes:
        return Counter(prefixes).most_common(1)[0][0]

    return "Partitura"


def get_pdf_files(directory="."):
    files = []
    for f in os.listdir(directory):
        if not f.lower().endswith(".pdf"):
            continue
        lower = f.lower()
        # Esclude i file uniti già generati
        if lower.endswith("- completo.pdf") or lower.startswith("documento_unito") or lower.startswith("partitura_completa_unita"):
            continue
        files.append(f)
    return files


def sort_pdf_files(file_list):
    return sorted(file_list, key=lambda f: get_sort_key(f, file_list))


def merge_pdf_files(directory, ordered_files, output_filename):
    writer = PdfWriter()
    for fname in ordered_files:
        filepath = os.path.join(directory, fname)
        writer.append(filepath)

    output_path = os.path.join(directory, output_filename)
    with open(output_path, "wb") as f_out:
        writer.write(f_out)
    writer.close()
    return output_path


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    pdf_files = get_pdf_files(folder)

    if not pdf_files:
        print(f"Nessun file PDF da unire trovato nella cartella '{folder}'.")
        return

    ordered = sort_pdf_files(pdf_files)
    title = detect_piece_title(ordered)
    output_filename = f"{title} - COMPLETO.pdf"

    print(f"\n--- ELENCO PDF ORDINATI ({len(ordered)} file) ---")
    output_lines = []
    for idx, fname in enumerate(ordered, 1):
        cat_idx, sub_idx, label = classify_instrument(fname, ordered)
        line = f"{idx:2d}. [{label}] {fname}"
        print(line)
        output_lines.append(line)

    # Salvataggio elenco testuale
    output_txt = os.path.join(folder, "ordine_pdf.txt")
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

    # Unione diretta nella stessa cartella
    print(f"\nUnione in corso di {len(ordered)} file in '{output_filename}'...")
    output_path = merge_pdf_files(folder, ordered, output_filename)
    print(f"[OK] File unito salvato con successo: {output_path}")


if __name__ == "__main__":
    main()
