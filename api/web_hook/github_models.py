from pydantic import BaseModel


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


class Sender(BaseModel):
    """
    Model representing the user who triggered the event.
    Parameters:
        login (str): The username of the sender
        id (int): The unique ID of the sender
    Returns:
        This class does not return anything
    """
    login: str
    id: int


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
    sender: Sender
    number: int
    
    class Config:
        extra = "ignore"
