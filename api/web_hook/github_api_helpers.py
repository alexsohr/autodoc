from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


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