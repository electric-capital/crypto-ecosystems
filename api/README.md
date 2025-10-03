\# Crypto Ecosystems REST API



A Flask-based REST API for accessing crypto ecosystem taxonomy data.



\## Installation



\### Prerequisites

\- Python 3.8 or higher

\- Zig (for building the main project)



\### Setup



1\. \*\*Install Python dependencies:\*\*

&nbsp;  ```bash

&nbsp;  cd api

&nbsp;  pip install -r requirements.txt

&nbsp;  ```



2\. \*\*Build the main project (required for data export):\*\*

&nbsp;  ```bash

&nbsp;  cd ..

&nbsp;  zig build

&nbsp;  ```



\## Running the API



\### Development Mode

```bash

cd api

python app.py

```



The API will start at `http://localhost:5000`



\### Production Mode (with Gunicorn)

```bash

pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 app:app

```



\## API Endpoints



\### 📚 Documentation

```

GET /

```

Returns API documentation and available endpoints.



\### 🌐 Get All Ecosystems

```

GET /api/ecosystems

```

Returns a list of all ecosystems with repository counts.



\*\*Response:\*\*

```json

{

&nbsp; "total": 150,

&nbsp; "ecosystems": \[

&nbsp;   {

&nbsp;     "name": "Bitcoin",

&nbsp;     "repository\_count": 523,

&nbsp;     "sub\_ecosystem\_count": 5,

&nbsp;     "sub\_ecosystems": \["Lightning", "Liquid"]

&nbsp;   }

&nbsp; ]

}

```



\### 🔍 Get Specific Ecosystem

```

GET /api/ecosystems/<ecosystem\_name>

```

Returns detailed information about a specific ecosystem.



\*\*Example:\*\*

```bash

curl http://localhost:5000/api/ecosystems/Bitcoin

```



\*\*Response:\*\*

```json

{

&nbsp; "name": "Bitcoin",

&nbsp; "repository\_count": 523,

&nbsp; "repositories": \["https://github.com/bitcoin/bitcoin", ...],

&nbsp; "sub\_ecosystems": \["Lightning", "Liquid"],

&nbsp; "tags": {

&nbsp;   "#protocol": 45,

&nbsp;   "#wallet": 32,

&nbsp;   "#developer-tool": 28

&nbsp; },

&nbsp; "sample\_repos": \[...]

}

```



\### 📦 Get All Repositories

```

GET /api/repositories?page=1\&per\_page=50

```

Returns paginated list of all repositories.



\*\*Query Parameters:\*\*

\- `page` (default: 1) - Page number

\- `per\_page` (default: 50, max: 200) - Items per page



\*\*Response:\*\*

```json

{

&nbsp; "total": 15234,

&nbsp; "page": 1,

&nbsp; "per\_page": 50,

&nbsp; "total\_pages": 305,

&nbsp; "repositories": \[...]

}

```



\### 🔎 Search Repositories

```

GET /api/repositories/search?q=<query>

```

Search repositories by name, ecosystem, or tags.



\*\*Example:\*\*

```bash

curl http://localhost:5000/api/repositories/search?q=ethereum

```



\*\*Response:\*\*

```json

{

&nbsp; "query": "ethereum",

&nbsp; "total": 234,

&nbsp; "results": \[...]

}

```



\### 🏷️ Get All Tags

```

GET /api/tags

```

Returns all available tags with their usage counts.



\*\*Response:\*\*

```json

{

&nbsp; "total\_tags": 15,

&nbsp; "tags": \[

&nbsp;   {"tag": "#protocol", "count": 423},

&nbsp;   {"tag": "#defi", "count": 312},

&nbsp;   {"tag": "#wallet", "count": 245}

&nbsp; ]

}

```



\### 📊 Get Statistics

```

GET /api/stats

```

Returns overall statistics about the dataset.



\*\*Response:\*\*

```json

{

&nbsp; "timestamp": "2025-10-03T16:30:00",

&nbsp; "total\_ecosystems": 156,

&nbsp; "total\_repositories": 15234,

&nbsp; "total\_tags": 15,

&nbsp; "top\_ecosystems": \[

&nbsp;   {"name": "Ethereum", "repository\_count": 3245},

&nbsp;   {"name": "Bitcoin", "repository\_count": 1523}

&nbsp; ],

&nbsp; "tag\_distribution": \[...],

&nbsp; "data\_freshness": {

&nbsp;   "cached": true,

&nbsp;   "cache\_age\_seconds": 245

&nbsp; }

}

```



\### ❤️ Health Check

```

GET /api/health

```

Returns API health status.



\*\*Response:\*\*

```json

{

&nbsp; "status": "healthy",

&nbsp; "timestamp": "2025-10-03T16:30:00",

&nbsp; "cache\_age\_seconds": 245

}

```



\## Usage Examples



\### Python

```python

import requests



\# Get all ecosystems

response = requests.get('http://localhost:5000/api/ecosystems')

ecosystems = response.json()



\# Search for Ethereum repositories

response = requests.get('http://localhost:5000/api/repositories/search?q=ethereum')

results = response.json()



\# Get statistics

response = requests.get('http://localhost:5000/api/stats')

stats = response.json()

print(f"Total repos: {stats\['total\_repositories']}")

```



\### JavaScript (Node.js)

```javascript

const axios = require('axios');



async function getEcosystems() {

&nbsp; const response = await axios.get('http://localhost:5000/api/ecosystems');

&nbsp; console.log(response.data);

}



async function searchRepos(query) {

&nbsp; const response = await axios.get(

&nbsp;   `http://localhost:5000/api/repositories/search?q=${query}`

&nbsp; );

&nbsp; return response.data.results;

}

```



\### cURL

```bash

\# Get all ecosystems

curl http://localhost:5000/api/ecosystems



\# Get Bitcoin ecosystem details

curl http://localhost:5000/api/ecosystems/Bitcoin



\# Search for DeFi projects

curl "http://localhost:5000/api/repositories/search?q=defi"



\# Get statistics

curl http://localhost:5000/api/stats

```



\## Caching



The API caches exported data for 1 hour (3600 seconds) to improve performance. After the cache expires, data is automatically refreshed from the latest migrations.



\## CORS



CORS is enabled for all origins, making the API accessible from web applications.



\## Error Handling



The API returns standard HTTP status codes:

\- `200` - Success

\- `400` - Bad Request (missing or invalid parameters)

\- `404` - Not Found (ecosystem or endpoint doesn't exist)

\- `500` - Internal Server Error



Error responses follow this format:

```json

{

&nbsp; "error": "Error description"

}

```



\## Docker Deployment



Create a `Dockerfile`:

```dockerfile

FROM python:3.11-slim



WORKDIR /app



\# Install Zig

RUN apt-get update \&\& apt-get install -y wget xz-utils

RUN wget https://ziglang.org/download/0.11.0/zig-linux-x86\_64-0.11.0.tar.xz

RUN tar -xf zig-linux-x86\_64-0.11.0.tar.xz

ENV PATH="/app/zig-linux-x86\_64-0.11.0:${PATH}"



\# Copy project files

COPY . .



\# Build project

RUN zig build



\# Install Python dependencies

RUN pip install -r api/requirements.txt



EXPOSE 5000



CMD \["python", "api/app.py"]

```



Build and run:

```bash

docker build -t crypto-ecosystems-api .

docker run -p 5000:5000 crypto-ecosystems-api

```



\## Contributing



See \[CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to this project.



\## License



MIT License - See \[LICENSE](../LICENSE) for details.

