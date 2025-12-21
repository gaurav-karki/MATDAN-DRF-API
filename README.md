# Matdan - Online Election System API

Matdan is a robust backend API for an online election and voting system, built with Django and Django REST Framework. It provides a secure and scalable foundation for managing elections, candidates, and user authentication, with a browsable API for easy interaction and testing.

## Features

-   **User Authentication**: Secure user registration and token-based authentication.
-   **Election Management**: Create, view, update, and delete elections. Only one election can be active at a time.
-   **Candidate Management**: Add candidates to specific elections, including name, party, and a photo.
-   **Image Uploads**: Supports uploading candidate photos, which are served as media files.
-   **Browsable API**: Interactive API documentation provided by Django REST Framework for easy endpoint testing.
-   **Filtering & Ordering**: Filter active elections and order results by start time or creation date.
-   **Custom Permissions**: Role-based access control (e.g., Admin-only for creating elections).
-   **Blockchain Ready**: Includes fields for integrating with smart contracts (Contract Address, ABI).

## Technology Stack

-   **Backend**: Python, Django
-   **API**: Django REST Framework (DRF)
-   **Database**: SQLite3 (default, configurable)
-   **Image Handling**: Pillow

---

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing.

### Prerequisites

-   Python 3.8+
-   Pip (Python package installer)
-   Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/gaurav-karki/MATDAN-DRF-API.git
    cd DjangoApp
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    *(First, ensure you have a `requirements.txt` file by running `pip freeze > requirements.txt`)*
    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply database migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Create a superuser to access the admin panel and create elections:**
    ```bash
    python manage.py createsuperuser
    ```

6.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```
    The API will be available at `http://127.0.0.1:8000/`.

---

## API Endpoints

Here are the primary API endpoints available in the project.

| Method | Endpoint                                       | Description                                  |
| :----- | :--------------------------------------------- | :------------------------------------------- |
| `POST` | `/api/v1/accounts/register/`                   | Register a new user.                         |
| `POST` | `/api-auth/`                                   | Obtain an authentication token.              |
| `GET`  | `/api/v1/elections/`                           | List all elections.                          |
| `POST` | `/api/v1/elections/`                           | Create a new election (Admin only).          |
| `GET`  | `/api/v1/elections/{election_id}/`             | Retrieve details of a specific election.     |
| `GET`  | `/api/v1/elections/{election_id}/candidates/`  | List all candidates for a specific election. |
| `POST` | `/api/v1/elections/{election_id}/candidates/`  | Add a new candidate to an election (Admin only). |

