#removes the page number section id 
#give chunks folder 
import re
import json
from pathlib import Path
from uuid import uuid4
from slugify import slugify  # pip install python-slugify

# ----------------------------
# CONFIG
# ----------------------------
input_md_path = r"legal_dataset_2.md"
output_root = Path("markdown_chunks3")
source_file = Path(input_md_path).stem

MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 2000
PREFERRED_CHUNK_SIZE = 800

def extract_prefix_and_title(heading):
    m = re.match(r'^([A-Za-z\dIVXLCDMivxlcdm]+(?:[.\-][A-Za-z\dIVXLCDMivxlcdm]+)*)(?:[)\.:]?)\s+(.*)', heading.strip())
    if m:
        return m.group(1), m.group(2)
    return None, heading.strip()

def is_table_content(text):
    lines = text.strip().split('\n')
    table_lines = [line for line in lines if re.match(r'^\|.*\|$', line.strip())]
    return len(table_lines) > 0

def create_section_folder_name(section):
    """Create folder name using section ID as primary identifier"""
    # Use first 8 characters of section ID for readability
    section_id_short = section["id"][:8]
    
    # Get prefix and title
    prefix, title = extract_prefix_and_title(section["heading"])
    
    # Create descriptive part
    if prefix:
        desc_part = f"{prefix}_{slugify(title)[:30]}"
    else:
        desc_part = slugify(section["heading"])[:30]
    
    # Add indicators
    indicators = []
    if section.get("has_table", False):
        indicators.append("TABLE")
    if section.get("has_image", False):
        indicators.append("IMG")
    
    # Combine parts: ID_PREFIX_TITLE[_INDICATORS]
    folder_name = f"{section_id_short}_{desc_part}"
    
    if indicators:
        folder_name += f"_[{'_'.join(indicators)}]"
    
    return folder_name[:100]

def create_chunk_filename(chunk, chunk_index):
    chunk_size = len(chunk["text"])
    if is_table_content(chunk["text"]):
        chunk_type = "table"
    elif chunk_size > MAX_CHUNK_SIZE * 0.8:
        chunk_type = "large"
    elif chunk_size < MIN_CHUNK_SIZE * 2:
        chunk_type = "small"
    else:
        chunk_type = "normal"
    filename = f"chunk_{chunk_index:03d}_{chunk_type}_{chunk_size}chars.json"
    return filename

def create_paragraph(text, section):
    return {
        "id": str(uuid4()),
        "text": text,
        "section_id": section["id"],
        "section_heading": section["heading"],
        "source_pdf": source_file,
        "has_table": section["has_table"],
        "has_image": section["has_image"],
        "char_count": len(text),
        "word_count": len(text.split()),
    }

def split_large_text(text, max_size=MAX_CHUNK_SIZE):
    if len(text) <= max_size:
        return [text]
    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > max_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 > max_size:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word
                        else:
                            chunks.append(word)
                    else:
                        temp_chunk += " " + word if temp_chunk else word
                if temp_chunk:
                    current_chunk = temp_chunk
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def merge_small_chunks(paragraphs, section):
    if not paragraphs:
        return []
    merged_chunks = []
    current_chunk_text = ""
    current_chunk_paragraphs = []
    chunk_counter = 1
    for para in paragraphs:
        para_text = para["text"]
        if is_table_content(para_text):
            if current_chunk_text:
                chunk = create_paragraph(
                    current_chunk_text.strip(),
                    section
                )
                merged_chunks.append(chunk)
                chunk_counter += 1
                current_chunk_text = ""
                current_chunk_paragraphs = []
            table_chunk = create_paragraph(para_text, section)
            merged_chunks.append(table_chunk)
            chunk_counter += 1
            continue
        combined_text = current_chunk_text + "\n\n" + para_text if current_chunk_text else para_text
        if len(combined_text) > PREFERRED_CHUNK_SIZE and current_chunk_text:
            if len(current_chunk_text) >= MIN_CHUNK_SIZE:
                chunk = create_paragraph(
                    current_chunk_text.strip(),
                    section
                )
                merged_chunks.append(chunk)
                chunk_counter += 1
                current_chunk_text = para_text
                current_chunk_paragraphs = [para]
            else:
                current_chunk_text = combined_text
                current_chunk_paragraphs.append(para)
        else:
            current_chunk_text = combined_text
            current_chunk_paragraphs.append(para)
        if len(current_chunk_text) > MAX_CHUNK_SIZE:
            split_texts = split_large_text(current_chunk_text)
            for i, split_text in enumerate(split_texts):
                chunk = create_paragraph(
                    split_text,
                    section
                )
                merged_chunks.append(chunk)
                chunk_counter += 1
            current_chunk_text = ""
            current_chunk_paragraphs = []
    if current_chunk_text:
        chunk = create_paragraph(
            current_chunk_text.strip(),
            section
        )
        merged_chunks.append(chunk)
    return merged_chunks

def chunk_markdown(md_text):
    sections = []
    current_section = None
    lines = md_text.splitlines()
    table_buffer = []
    raw_paragraphs = []
    for line in lines:
        stripped = line.strip()
        heading_match = re.match(r"^(#{2,6})\s+(.*)", line)
        if heading_match:
            if table_buffer:
                table_text = "\n".join(table_buffer)
                para_obj = {"text": table_text}
                raw_paragraphs.append(para_obj)
                table_buffer.clear()
            if current_section:
                current_section["raw_paragraphs"] = raw_paragraphs
                sections.append(current_section)
            current_section = {
                "id": str(uuid4()),
                "heading": heading_match.group(2).strip(),
                "paragraphs": [],
                "content": "",
                "has_table": False,
                "has_image": False,
            }
            raw_paragraphs = []
            continue
        if current_section is None:
            current_section = {
                "id": str(uuid4()),
                "heading": "PREFACE",
                "paragraphs": [],
                "content": "",
                "has_table": False,
                "has_image": False,
            }
        if not stripped:
            if table_buffer:
                table_text = "\n".join(table_buffer)
                para_obj = {"text": table_text}
                raw_paragraphs.append(para_obj)
                table_buffer.clear()
            continue
        if "<!-- image -->" in stripped:
            current_section["has_image"] = True
        if re.match(r"^\|.*\|$", stripped):
            table_buffer.append(line)
            current_section["has_table"] = True
            continue
        else:
            if table_buffer:
                table_text = "\n".join(table_buffer)
                para_obj = {"text": table_text}
                raw_paragraphs.append(para_obj)
                current_section["content"] += table_text + "\n"
                table_buffer.clear()
        if stripped:
            para_obj = {"text": stripped}
            raw_paragraphs.append(para_obj)
            current_section["content"] += line + "\n"
    if table_buffer:
        table_text = "\n".join(table_buffer)
        para_obj = {"text": table_text}
        raw_paragraphs.append(para_obj)
        current_section["has_table"] = True
    if current_section:
        current_section["raw_paragraphs"] = raw_paragraphs
        sections.append(current_section)
    for section in sections:
        section["paragraphs"] = merge_small_chunks(section["raw_paragraphs"], section)
        for para in section["paragraphs"]:
            para["has_table"] = section["has_table"]
            para["has_image"] = section["has_image"]
    return sections

def assign_section_parents_and_subsections(sections):
    prefix_to_section = {}
    last_numbered_section = None
    for section in sections:
        prefix, _ = extract_prefix_and_title(section["heading"])
        section["parent_id"] = None
        if prefix:
            prefix_parts = prefix.split(".")
            parent = None
            for i in range(len(prefix_parts) - 1, 0, -1):
                parent_prefix = ".".join(prefix_parts[:i])
                if parent_prefix in prefix_to_section:
                    parent = prefix_to_section[parent_prefix]
                    break
            if parent:
                section["parent_id"] = parent["id"]
            prefix_to_section[prefix] = section
            last_numbered_section = section
        else:
            if last_numbered_section:
                section["parent_id"] = last_numbered_section["id"]
    sections_by_id = {section["id"]: section for section in sections}
    # Track children (subsections) for each section
    for section in sections:
        section["subsections"] = []
    for section in sections:
        parent_id = section.get("parent_id")
        if parent_id and parent_id in sections_by_id:
            parent_section = sections_by_id[parent_id]
            parent_section["subsections"].append({
                "id": section["id"],
                "heading": section["heading"],
                "path": create_section_folder_name(section)
            })
    return sections_by_id

def get_full_folder_path(section, sections_by_id, pdf_dir):
    """Create folder path using section ID as primary identifier"""
    # For hierarchical structure, we'll use section IDs but maintain hierarchy
    parts = []
    current = section
    while current:
        folder = create_section_folder_name(current)
        parts.append(folder)
        parent_id = current.get("parent_id")
        if parent_id:
            current = sections_by_id.get(parent_id)
        else:
            current = None
    return pdf_dir.joinpath(*reversed(parts))

def run_chunking(input_md_path, output_root):
    if not Path(input_md_path).exists():
        print(f"[ERROR] File not found: {input_md_path}")
        return
    with open(input_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    doc_timestamp = Path(input_md_path).stat().st_mtime
    pdf_dir = output_root / f"{source_file}_processed"
    if (pdf_dir / ".done").exists():
        print(f"[SKIP] Already processed: {source_file}")
        return
    pdf_dir.mkdir(parents=True, exist_ok=True)
    sections = chunk_markdown(md_text)
    sections_by_id = assign_section_parents_and_subsections(sections)
    
    # Create section ID mapping file for easy access
    section_id_map = {}
    for section in sections:
        section_id_map[section["id"]] = {
            "heading": section["heading"],
            "folder_path": create_section_folder_name(section),
            "full_folder_path": str(get_full_folder_path(section, sections_by_id, pdf_dir).relative_to(pdf_dir)),
            "has_table": section["has_table"],
            "has_image": section["has_image"],
            "chunk_count": len(section["paragraphs"])
        }
    
    # Save section ID mapping
    with open(pdf_dir / "section_id_mapping.json", "w", encoding="utf-8") as f:
        json.dump(section_id_map, f, ensure_ascii=False, indent=2)

    doc_summary = {
        "source_file": source_file,
        "total_sections": len(sections),
        "total_chunks": sum(len(s["paragraphs"]) for s in sections),
        "sections_with_tables": sum(1 for s in sections if s["has_table"]),
        "sections_with_images": sum(1 for s in sections if s["has_image"]),
        "processing_config": {
            "min_chunk_size": MIN_CHUNK_SIZE,
            "preferred_chunk_size": PREFERRED_CHUNK_SIZE,
            "max_chunk_size": MAX_CHUNK_SIZE
        },
        "section_id_mapping_file": "section_id_mapping.json"
    }
    with open(pdf_dir / "document_summary.json", "w", encoding="utf-8") as f:
        json.dump(doc_summary, f, ensure_ascii=False, indent=2)

    # NEW: Prepare a global chunks directory for all chunks in doc order
    chunks_dir = pdf_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    global_chunk_counter = 1

    for idx, section in enumerate(sections, 1):
        section_dir = get_full_folder_path(section, sections_by_id, pdf_dir)
        section_dir.mkdir(parents=True, exist_ok=True)
        section_meta_path = section_dir / "section_meta.json"
        section_meta = {
            "section_id": section["id"],
            "heading": section["heading"],
            "parent_id": section.get("parent_id"),
            "num_paragraphs": len(section["paragraphs"]),
            "source_pdf": source_file,
            "has_table": section["has_table"],
            "has_image": section["has_image"],
            "content": section["content"].strip(),
            "subsections": section["subsections"],
            "folder_name": create_section_folder_name(section),
            "chunk_stats": {
                "total_chunks": len(section["paragraphs"]),
                "avg_chunk_size": sum(len(p["text"]) for p in section["paragraphs"]) / len(section["paragraphs"]) if section["paragraphs"] else 0,
                "size_distribution": {
                    "small": len([p for p in section["paragraphs"] if len(p["text"]) < MIN_CHUNK_SIZE * 2]),
                    "normal": len([p for p in section["paragraphs"] if MIN_CHUNK_SIZE * 2 <= len(p["text"]) <= MAX_CHUNK_SIZE * 0.8]),
                    "large": len([p for p in section["paragraphs"] if len(p["text"]) > MAX_CHUNK_SIZE * 0.8]),
                }
            }
        }
        with open(section_meta_path, "w", encoding="utf-8") as f:
            json.dump(section_meta, f, ensure_ascii=False, indent=2)
        print(f"[SECTION] {section['id'][:8]} - {section['heading']} - {len(section['paragraphs'])} chunks")

        for chunk_idx, para in enumerate(section["paragraphs"], 1):
            chunk_filename = create_chunk_filename(para, chunk_idx)
            chunk_file = section_dir / chunk_filename
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(para, f, ensure_ascii=False, indent=2)
            print(f"[CHUNK] {chunk_filename} - {len(para['text'])} chars")

            # Write to global chunks folder in order
            global_chunk_filename = f"{global_chunk_counter:05d}__{section['id']}__{para['id']}.json"
            global_chunk_counter += 1
            with open(chunks_dir / global_chunk_filename, "w", encoding="utf-8") as f:
                json.dump(para, f, ensure_ascii=False, indent=2)

    (pdf_dir / ".done").write_text("done")
    print(f"\n[DONE] Processing completed for: {source_file}")
    print("[INFO] Output structure:")
    print(f"  📁 {pdf_dir.name}/")
    print("    📄 document_summary.json")
    print("    📄 section_id_mapping.json")
    print("    📁 chunks/")
    for idx, section in enumerate(sections, 1):
        section_dir = get_full_folder_path(section, sections_by_id, pdf_dir)
        print(f"    📁 {section_dir.relative_to(pdf_dir)}/")
        print("      📄 section_meta.json")
        print(f"      📄 {len(section['paragraphs'])} chunk files")
        print(f"      [Section ID: {section['id']}]")
    print(f"\n[CONFIG] Chunk sizes: MIN={MIN_CHUNK_SIZE}, PREFERRED={PREFERRED_CHUNK_SIZE}, MAX={MAX_CHUNK_SIZE}")

run_chunking(input_md_path, output_root)