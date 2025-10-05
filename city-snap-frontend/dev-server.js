const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 5173;
const ROOT = path.join(__dirname);

function send(res, status, content, type='text/html') {
  res.writeHead(status, { 'Content-Type': type });
  res.end(content);
}

const server = http.createServer((req, res) => {
  const urlPath = req.url === '/' ? '/index.html' : req.url;
  const filePath = path.join(ROOT, decodeURIComponent(urlPath.split('?')[0]));
  if (!filePath.startsWith(ROOT)) return send(res, 403, 'Forbidden', 'text/plain');

  fs.readFile(filePath, (err, data) => {
    if (err) {
      if (err.code === 'ENOENT') return send(res, 404, 'Not found', 'text/plain');
      return send(res, 500, 'Server error', 'text/plain');
    }
    const ext = path.extname(filePath).toLowerCase();
    const map = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
    send(res, 200, data, map[ext] || 'application/octet-stream');
  });
});

server.listen(PORT, () => {
  console.log(`Frontend dev server running at http://localhost:${PORT}`);
});
