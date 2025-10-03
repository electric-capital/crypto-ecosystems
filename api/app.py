from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import subprocess
from collections import defaultdict, Counter
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Cache for exported data
_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 3600  # Cache for 1 hour
}

def load_ecosystem_data():
    """Load ecosystem data from export or cache"""
    current_time = datetime.now()
    
    # Return cached data if still valid
    if _cache['data'] and _cache['timestamp']:
        time_diff = (current_time - _cache['timestamp']).seconds
        if time_diff < _cache['ttl']:
            return _cache['data']
    
    # Generate fresh export
    export_file = 'api_export.jsonl'
    
    try:
        # Run export command
        if os.name == 'nt':  # Windows
            subprocess.run(['cmd', '/c', 'run.sh', 'export', export_file], check=True)
        else:  # Linux/Mac
            subprocess.run(['./run.sh', 'export', export_file], check=True)
        
        # Load data
        data = []
        with open(export_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        
        # Update cache
        _cache['data'] = data
        _cache['timestamp'] = current_time
        
        # Clean up export file
        os.remove(export_file)
        
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return _cache['data'] if _cache['data'] else []

@app.route('/')
def index():
    """API documentation"""
    return jsonify({
        'name': 'Crypto Ecosystems API',
        'version': '1.0.0',
        'description': 'REST API for crypto ecosystem taxonomy data',
        'endpoints': {
            '/': 'API documentation (this page)',
            '/api/ecosystems': 'List all ecosystems',
            '/api/ecosystems/<name>': 'Get specific ecosystem details',
            '/api/repositories': 'List all repositories',
            '/api/repositories/search?q=<query>': 'Search repositories',
            '/api/stats': 'Get overall statistics',
            '/api/tags': 'List all available tags',
            '/api/health': 'API health check'
        },
        'documentation': 'https://github.com/PROFADAM/crypto-ecosystems'
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cache_age_seconds': (datetime.now() - _cache['timestamp']).seconds if _cache['timestamp'] else None
    })

@app.route('/api/ecosystems')
def get_ecosystems():
    """Get list of all ecosystems with their repository counts"""
    data = load_ecosystem_data()
    
    # Group by ecosystem
    ecosystems = defaultdict(lambda: {'repos': [], 'sub_ecosystems': set()})
    
    for item in data:
        eco_name = item['eco_name']
        ecosystems[eco_name]['repos'].append(item['repo_url'])
        
        # Track sub-ecosystems
        if item.get('branch'):
            for branch in item['branch']:
                ecosystems[eco_name]['sub_ecosystems'].add(branch)
    
    # Format response
    result = []
    for name, info in sorted(ecosystems.items()):
        result.append({
            'name': name,
            'repository_count': len(info['repos']),
            'sub_ecosystem_count': len(info['sub_ecosystems']),
            'sub_ecosystems': sorted(list(info['sub_ecosystems']))
        })
    
    return jsonify({
        'total': len(result),
        'ecosystems': result
    })

@app.route('/api/ecosystems/<ecosystem_name>')
def get_ecosystem(ecosystem_name):
    """Get detailed information about a specific ecosystem"""
    data = load_ecosystem_data()
    
    # Filter by ecosystem name (case-insensitive)
    ecosystem_data = [
        item for item in data 
        if item['eco_name'].lower() == ecosystem_name.lower()
    ]
    
    if not ecosystem_data:
        return jsonify({'error': 'Ecosystem not found'}), 404
    
    # Collect statistics
    repos = [item['repo_url'] for item in ecosystem_data]
    tags = []
    for item in ecosystem_data:
        tags.extend(item.get('tags', []))
    
    sub_ecosystems = set()
    for item in ecosystem_data:
        if item.get('branch'):
            sub_ecosystems.update(item['branch'])
    
    return jsonify({
        'name': ecosystem_data[0]['eco_name'],
        'repository_count': len(repos),
        'repositories': repos,
        'sub_ecosystems': sorted(list(sub_ecosystems)),
        'tags': dict(Counter(tags)),
        'sample_repos': repos[:10]  # First 10 repos as sample
    })

@app.route('/api/repositories')
def get_repositories():
    """Get all repositories with pagination"""
    data = load_ecosystem_data()
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 200)  # Max 200 per page
    
    start = (page - 1) * per_page
    end = start + per_page
    
    total = len(data)
    repos = data[start:end]
    
    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'repositories': repos
    })

@app.route('/api/repositories/search')
def search_repositories():
    """Search repositories by query"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    data = load_ecosystem_data()
    
    # Search in repo URL and ecosystem name
    results = [
        item for item in data
        if query in item['repo_url'].lower() or 
           query in item['eco_name'].lower() or
           any(query in tag.lower() for tag in item.get('tags', []))
    ]
    
    return jsonify({
        'query': query,
        'total': len(results),
        'results': results
    })

@app.route('/api/tags')
def get_tags():
    """Get all available tags with their counts"""
    data = load_ecosystem_data()
    
    tags = []
    for item in data:
        tags.extend(item.get('tags', []))
    
    tag_counts = Counter(tags)
    
    return jsonify({
        'total_tags': len(tag_counts),
        'tags': [
            {'tag': tag, 'count': count}
            for tag, count in tag_counts.most_common()
        ]
    })

@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    data = load_ecosystem_data()
    
    # Calculate statistics
    ecosystems = set(item['eco_name'] for item in data)
    repos = set(item['repo_url'] for item in data)
    
    tags = []
    for item in data:
        tags.extend(item.get('tags', []))
    
    # Top ecosystems by repo count
    eco_counts = Counter(item['eco_name'] for item in data)
    top_ecosystems = [
        {'name': name, 'repository_count': count}
        for name, count in eco_counts.most_common(10)
    ]
    
    # Tag distribution
    tag_counts = Counter(tags)
    tag_distribution = [
        {'tag': tag, 'count': count}
        for tag, count in tag_counts.most_common(10)
    ]
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'total_ecosystems': len(ecosystems),
        'total_repositories': len(repos),
        'total_tags': len(set(tags)),
        'top_ecosystems': top_ecosystems,
        'tag_distribution': tag_distribution,
        'data_freshness': {
            'cached': _cache['timestamp'] is not None,
            'cache_age_seconds': (datetime.now() - _cache['timestamp']).seconds if _cache['timestamp'] else None
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting Crypto Ecosystems API...")
    print("📡 API will be available at: http://localhost:5000")
    print("📚 Documentation: http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)