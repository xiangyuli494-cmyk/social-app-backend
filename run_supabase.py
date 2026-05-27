import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app

if __name__ == '__main__':
    print('Backend starting with Supabase REST API')
    print('Connected to Supabase PostgreSQL')
    print('Server starting on http://0.0.0.0:5000')
    app.run(host='0.0.0.0', port=5000, debug=True)
