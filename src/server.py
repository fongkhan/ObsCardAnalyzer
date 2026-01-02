from flask import Flask, jsonify, request, render_template_string
import threading

app = Flask(__name__)
_latest = []

@app.route('/api/update', methods=['POST'])
def api_update():
    global _latest
    data = request.get_json()
    if not data:
        return ("", 400)
    # keep a short history
    _latest.insert(0, data)
    _latest = _latest[:50]
    return ("", 204)

@app.route('/api/latest')
def api_latest():
    return jsonify(_latest)

_overlay_html = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Card Overlay</title>
    <style>
      body { background: rgba(0,0,0,0); color: white; font-family: Arial, sans-serif }
      .card { background: rgba(0,0,0,0.6); padding: 8px; border-radius: 6px; margin: 6px }
    </style>
  </head>
  <body>
    <div id="container"></div>
    <script>
      async function fetchLatest(){
        const r = await fetch('/api/latest');
        const json = await r.json();
        const container = document.getElementById('container');
        container.innerHTML = '';
        for (const item of json.slice(0,5)){
          const el = document.createElement('div'); el.className='card';
          el.innerHTML = `<strong>${item.name||'?'}</strong><div>${item.set||''}</div><div>${item.price||''}</div><div style='font-size:small'>${item.notes||''}</div>`;
          container.appendChild(el);
        }
      }
      setInterval(fetchLatest, 1000);
      fetchLatest();
    </script>
  </body>
</html>
"""

@app.route('/overlay')
def overlay():
    return render_template_string(_overlay_html)

def run_server(host='127.0.0.1', port=5000):
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == '__main__':
    print('Starting overlay server on http://127.0.0.1:5000/overlay')
    run_server()
