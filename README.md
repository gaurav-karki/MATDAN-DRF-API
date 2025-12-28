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
-   **Database**: PostgreSQL
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
| `POST` | `/api-auth/login`                                   | Obtain an authentication token.              |
| `GET`  | `/api/v1/elections/`                           | List all elections.                          |
| `POST` | `/api/v1/elections/`                           | Create a new election (Admin only).          |
| `GET`  | `/api/v1/elections/{election_id}/`             | Retrieve details of a specific election.     |
| `GET`  | `/api/v1/elections/{election_id}/candidates/`  | List all candidates for a specific election. |
| `POST` | `/api/v1/elections/{election_id}/candidates/`  | Add a new candidate to an election (Admin only). |
| `POST` | `/api/v1/votes/{election_id}/vote/`           | Cast vote to a candidate in a active election |
| `GET`  | `/api/v1/votes/{election_id}/results/`        | View results of the election                  |
| `GET`  | `/api/v1/votes/{election_id}/my-vote/`        | View the details of the vote casted by you.   |
| `GET` | `/api/v1/blockchain/status`                    | View if blockchain service have been sucessfully initialized |
| `POST` | `/api/v1/blockchain/elections/{election_id}/sync` | Sync the election and candidates to blockchain|
| `POST` | `/api/v1/blockchain/elections/{election_id}/activate` | Activate or decativate the synced election in blockchain|
| `POST` | `/api/v1/blockchain/elections/{election_id}/results` | Activate or decativate the synced election in blockchain|
| `GET` | `/api/v1/blockchain/votes/verify`                     | View or verify the vote you casted                     |



# Blockchain service
- **Download Ganache**
`or`
- **Download Ganache CLI. You have to have node installed in your system**
`npm install ganache --save-dev`

### To run Blockchain service
- create `.env` file in your root directory.
    -  `BLOCKCHAIN_PROVIDER_URL=http://127.0.0.1:8545`
    -  `BLOCKCHAIN_PRIVATE_KEY= {your_private_key from ganache CLI}`
    -  `VOTING_CONTRACT_ADDRESS = {contract_address}`
    -  `BLOCKCHAIN_CHAIN_ID=1337`
    -  `DEBUG=TRUE`

- To start Ganache on your terminal. Write
    `ganache` or custom start method

- To obtain contract address
    `python manage.py shell`
    `from blockchain.deploy_contract import deploy_contract`
    `contract_address = deploy_contract()`
    `print(contract_address)`
