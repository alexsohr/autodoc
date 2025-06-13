from pydantic import BaseModel
from typing import List, Optional, Dict, Any



class Owner(BaseModel):
    """
    Model representing a GitHub repository owner.
    Parameters:
        login (str): The username of the owner
        id (int): The unique ID of the owner
    Returns:
        This class does not return anything
    """
    login: str
    id: int


class Repository(BaseModel):
    """
    Model representing a GitHub repository.
    Parameters:
        id (int): The unique ID of the repository
        full_name (str): The full name of the repository (e.g., 'octocat/Hello-World')
        owner (Owner): The owner of the repository
    Returns:
        This class does not return anything
    """
    id: int
    full_name: str
    owner: Owner
    html_url: str
    default_branch: str


class GithubPushEvent(BaseModel):
    """
    Model for GitHub push event webhook payload.
    Parameters:
        action (str): The action that was performed (e.g., 'opened', 'closed', 'edited')
        repository (Repository): The repository where the push belongs
        sender (Sender): The user who triggered the event
        number (int): The number of the issue
    Returns:
        This class does not return anything
    """
    action: str
    repository: Repository
    number: int
    
    class Config:
        extra = "ignore"

class WikiStructure:
    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        pages: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
        root_sections: List[str]
    ):
        self.id = id
        self.title = title
        self.description = description
        self.pages = pages
        self.sections = sections
        self.rootSections = root_sections

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "pages": self.pages,
            "sections": self.sections,
            "rootSections": self.rootSections
        }
