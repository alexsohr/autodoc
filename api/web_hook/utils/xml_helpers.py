import re
import logging
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict

# Configure logger
logger = logging.getLogger(__name__)
# Basic config if not already set by another module
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)


def extract_wiki_structure_xml(wiki_structure_response: str, logger_instance=None) -> str:
    """
    Clean up the AI response and extract the <wiki_structure>...</wiki_structure> XML block.
    Raises ValueError if the response is empty or no valid XML is found.
    """
    if logger_instance is None:
        logger_instance = logger # Use module-level logger if none provided

    if not wiki_structure_response or str(wiki_structure_response).strip() == "":
        logger_instance.error("Wiki structure response is empty - this indicates an issue with the model call")
        raise ValueError("Wiki structure response is empty")

    wiki_structure_response = str(wiki_structure_response)
    # Remove markdown ```xml ... ``` blocks
    wiki_structure_response = re.sub(r'^```(?:xml)?\s*', '', wiki_structure_response, flags=re.IGNORECASE)
    wiki_structure_response = re.sub(r'```\s*$', '', wiki_structure_response, flags=re.IGNORECASE)

    match = re.search(r"<wiki_structure>[\s\S]*?</wiki_structure>", wiki_structure_response, re.MULTILINE)

    if not match:
        logger_instance.error(f"No valid XML structure found in AI response. Response length: {len(wiki_structure_response)}")
        logger_instance.debug(f"Full response for XML extraction check: {wiki_structure_response}")
        if len(wiki_structure_response) > 500:
             logger_instance.debug(f"First 500 chars of response: {wiki_structure_response[:500]}")
        raise ValueError("No valid XML structure found in AI response")

    xml_match = match.group(0)
    # Remove control characters that are invalid in XML
    xml_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_match)
    return xml_text


def parse_wiki_structure(xml_text: str) -> Tuple[str, str, List[dict]]:
    """
    Parse the XML wiki structure and extract title, description, and pages.
    Parameters:
        xml_text (str): XML string
    Returns:
        Tuple[str, str, List[dict]]: (title, description, pages)
    """
    root = ET.fromstring(xml_text)
    title = root.findtext('title', default='')
    description = root.findtext('description', default='')
    pages = []
    for page_el in root.findall('.//page'):
        page = {
            'id': page_el.get('id', ''),
            'title': page_el.findtext('title', default=''),
            'description': page_el.findtext('description', default=''),
            'importance': page_el.findtext('importance', default='medium'),
            'file_paths': [fp.text for fp in page_el.findall('.//file_path') if fp.text],
            'related_pages': [rel.text for rel in page_el.findall('.//related') if rel.text],
        }
        pages.append(page)
    return title, description, pages


def parse_wiki_sections_from_xml(sections_els) -> Tuple[List[Dict], List[str]]:
    """
    Parse <section> elements from XML and return (sections_list, root_section_ids_list).
    """
    sections = []
    all_section_ids = set()
    referenced_section_ids = set()

    if not sections_els:
        logger.info("No <section> elements found in XML to parse.")
        return [], []

    for i, section_el in enumerate(sections_els):
        id_ = section_el.get('id', f'section-{i + 1}')
        all_section_ids.add(id_)
        title_el = section_el.find('title')
        page_ref_els = section_el.findall('.//page_ref')
        section_ref_els = section_el.findall('.//section_ref')

        title = title_el.text if title_el is not None and title_el.text is not None else f'Untitled Section {id_}'

        pages_in_section = [el.text for el in page_ref_els if el.text]
        subsections_refs = [el.text for el in section_ref_els if el.text]

        for ref_id in subsections_refs:
            referenced_section_ids.add(ref_id)

        section = {
            'id': id_,
            'title': title,
            'pages': pages_in_section,
            'subsections': subsections_refs if subsections_refs else []
        }
        sections.append(section)

    root_sections_ids = list(all_section_ids - referenced_section_ids)

    if not sections and sections_els: # sections_els was not empty but sections list is
        logger.warning("No sections were successfully parsed despite presence of <section> elements.")

    if not root_sections_ids and sections:
        logger.info("No specific root sections identified (e.g., all sections are sub-sections or form a flat list).")
        # If all sections are present and none are referenced, they are all roots.
        if not referenced_section_ids:
             root_sections_ids = list(all_section_ids)
             logger.info("Treating all parsed sections as root sections as no inter-section references were found.")

    return sections, root_sections_ids
