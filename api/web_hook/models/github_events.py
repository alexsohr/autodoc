from pydantic import BaseModel
from typing import List, Dict, Any



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
        html_url (str): The URL of the repository
        default_branch (str): The default branch of the repository
    Returns:
        This class does not return anything
    """
    id: int
    full_name: str
    owner: Owner
    html_url: str
    default_branch: str

class Base(BaseModel):
    ref: str

class PullRequest(BaseModel):
    merged: bool
    base: Base


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
    pull_request: PullRequest
    
    class Config:
        extra = "ignore"


class WikiPageDetail(BaseModel):
    """Represents a single page within the wiki structure, including its content."""
    id: str
    title: str
    description: str
    importance: str # Should ideally be an Enum: 'high', 'medium', 'low'
    file_paths: List[str]
    related_pages: List[str]
    content: str = "" # Default to empty string, will be filled in by generation

    class Config:
        extra = "ignore"
        # If there's a need to alias filePaths to file_paths during serialization/deserialization
        # from an external source that uses camelCase, Pydantic v2 allows field_serializer
        # or alias_generator. For now, keeping it simple.


class WikiSection(BaseModel):
    """Represents a section in the wiki, which can contain pages and subsections."""
    id: str
    title: str
    pages: List[str] # List of page IDs
    subsections: List[str] = [] # List of subsection IDs, defaults to empty

    class Config:
        extra = "ignore"


class WikiStructure(BaseModel):
    """
    Model representing the structure of a generated wiki.
    """
    id: str
    title: str
    description: str
    pages: List[WikiPageDetail] # A list of Pydantic models
    sections: List[WikiSection] # A list of Pydantic models
    root_sections: List[str]

    class Config:
        extra = "ignore"
