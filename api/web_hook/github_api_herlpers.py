from typing import List, Dict


def parse_wiki_pages_from_xml(pages_els) -> List[Dict]:
    """
    Parse <page> elements from XML and return a list of page dicts.
    """
    pages = []
    for page_el in pages_els:
        id_ = page_el.get('id', f'page-{len(pages) + 1}')
        title_el = page_el.find('title')
        importance_el = page_el.find('importance')
        file_path_els = page_el.findall('.//file_path')
        related_els = page_el.findall('.//related')
        title = title_el.text if title_el is not None else ''
        importance = 'medium'
        if importance_el is not None:
            if importance_el.text == 'high':
                importance = 'high'
            elif importance_el.text == 'medium':
                importance = 'medium'
            else:
                importance = 'low'
        file_paths = [el.text for el in file_path_els if el.text]
        related_pages = [el.text for el in related_els if el.text]
        pages.append({
            'id': id_,
            'title': title,
            'content': '',  # Will be generated later
            'filePaths': file_paths,
            'importance': importance,
            'relatedPages': related_pages
        })
    return pages

def parse_wiki_sections_from_xml(sections_els):
    """
    Parse <section> elements from XML and return (sections, root_sections) lists.
    """
    sections = []
    root_sections = []
    if sections_els:
        for section_el in sections_els:
            id_ = section_el.get('id', f'section-{len(sections) + 1}')
            title_el = section_el.find('title')
            page_ref_els = section_el.findall('.//page_ref')
            section_ref_els = section_el.findall('.//section_ref')
            title = title_el.text if title_el is not None else ''
            pages = [el.text for el in page_ref_els if el.text]
            subsections = [el.text for el in section_ref_els if el.text]
            section = {
                'id': id_,
                'title': title,
                'pages': pages,
                'subsections': subsections if subsections else None
            }
            sections.append(section)
            # Check if this is a root section (not referenced by any other section)
            is_referenced = False
            for other_section in sections_els:
                other_section_refs = other_section.findall('.//section_ref')
                for ref in other_section_refs:
                    if ref.text == id_:
                        is_referenced = True
            if not is_referenced:
                root_sections.append(id_)
    return sections, root_sections 