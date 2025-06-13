def parse_wiki_pages_from_xml(pages_els):
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