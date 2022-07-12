# Simple REST API for invoking draw.io to convert its file format
# to an image file.

# Thanks to https://github.com/jgraph/drawio-desktop/issues/127#issuecomment-520053181
# for providing the critical information of how to build a working containerized
# draw.io desktop binary.

from flask import Flask,request,send_file,g
from flask.logging import create_logger
from flask_expects_json import expects_json
from flask_redoc import Redoc
import tempfile
import os, subprocess, re, shutil, sys

app = Flask(__name__)
log = create_logger(app)

supported_formats = ['png', 'jpeg', 'svg', 'pdf']

pages_regex = r'^([0-9]{1,4})(\.\.([0-9]{1,4}))?$'

schema = {
    'type': 'object',
    'properties': {
        'source': {'type': 'string'},
        'format': {'type': 'string', 'enum': supported_formats, 'default': 'png'},
        'quality': {'type': 'integer', 'minimum': 1, 'maximum': 100},
        'transparent': {'type': 'boolean'},
        'embed': {'type': 'boolean'},
        'border': {'type': 'integer', 'minimum': 0, 'maximum': 10000},
        'scale': {'type': 'number', 'minimum': 0, 'exclusiveMinimum': True, 'maximum': 5},
        'width': {'type': 'integer', 'minimum': 10, 'maximum': 131072},
        'height': {'type': 'integer', 'minimum': 10, 'maximum': 131072},
        'crop': {'type': 'boolean'},
    },
    'required': ['source']
}

redoc = Redoc(app, 'openapi.yaml')

@app.errorhandler(400)
def bad_request(error):
    try:
        return {'error': error.description.message}, 400
    except AttributeError: 
        return {'error': error.description}, 400

def convert_common(req, source, fmt):
    if 'quality' in req and fmt != 'jpeg':
        return {'message': f"only jpeg format supports quality"}, 400
    if 'transparent' in req and fmt != 'png':
        return {'message': f"only png format supports transparent"}, 400
    if 'embed' in req and fmt != 'png':
        return {'message': f"only png format supports embed"}, 400
    if 'crop' in req and fmt != 'pdf':
        return {'message': f"only pdf format supports crop"}, 400
    
    tmpdir = tempfile.mkdtemp()
    saved_umask = os.umask(0o0077)
    infile = os.path.join(tmpdir, "input.drawio")
    outbase = f"output.{fmt}"
    outfile = os.path.join(tmpdir, outbase)
    log.info("%s -> %s", infile, outfile)
    try:
        with open(infile, "wb") as tmp:
            tmp.write(source)

        cmd = ['xvfb-run', '-a', '/opt/drawio/drawio', '-x', '-f', fmt, '-o', outfile]
        if 'quality' in req:
            cmd.extend(['-q', str(req['quality'])])
        if 'transparent' in req and req['transparent']:
            cmd.append('-t')
        if 'embed' in req and req['embed']:
            cmd.append('-e')
        if 'border' in req:
            cmd.extend(['-b', str(req['border'])])
        if 'scale' in req:
            cmd.extend(['-s', str(req['scale'])])
        if 'width' in req:
            cmd.extend(['--width', str(req['width'])])
        if 'height' in req:
            cmd.extend(['--height', str(req['height'])])
        if 'crop' in req and req['crop']:
            cmd.append('--crop')

        # this must be the next-to-last parameter
        cmd.append(infile)

        # this must be the last parameter
        cmd.append('--no-sandbox')

        result = subprocess.run(cmd, universal_newlines=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        if len(result.stderr) > 0:
            print(result.stderr, file=sys.stderr, end='', flush=True)
            error = result.stderr.splitlines()[0]
            if 'Out of memory' in error:
                code = 413
            elif 'Xvfb failed to start' in error:
                code = 500
            else:
                code = 400
            return {'message': f'Error executing draw.io: {error}'}, code

        line = result.stdout.splitlines()[-1]
        if f" -> {outfile}" not in line:
            return {'message': f'Error processing input: {line}'}, 400

        return send_file(outfile, attachment_filename=outbase)
    finally:
        os.umask(saved_umask)
        shutil.rmtree(tmpdir)

@app.route('/convert', methods=['POST'])
@expects_json(schema, fill_defaults=True)
def convert_json():
    req = g.data
    source = req['source'].encode('utf-8')
    fmt = req['format']
    return convert_common(req, source, fmt)

def try_to_int(req, prop, minimum, maximum):
    if prop in req:
        try:
            val = int(req[prop])
            if val < minimum or val > maximum:
                return f'{prop} must be an integer from {minimum}-{maximum}'
            req[prop] = val
        except ValueError:
            return f'{prop} must be an integer from {minimum}-{maximum}'
    return None

def try_to_bool(req, prop):
    if prop in req:
        val = req[prop].lower()
        if val == 'true':
            req[prop] = True
        elif val == 'false':
            req[prop] = False
        else:
            return f'{prop} must be true or false'
    return None

def try_to_float(req, prop, maximum):
    if prop in req:
        try:
            val = float(req[prop])
            if val <= 0.0 or val > maximum:
                return f'{prop} must be an integer from 0-{maximum}'
            req[prop] = val
        except ValueError:
            return f'{prop} must be an integer from 0-{maximum}'
    return None

@app.route('/convert_file', methods=['POST'])
def convert_file():
    req = request.args.copy() if request.args else {}
    error = try_to_int(req, 'quality', 1, 100) or \
            try_to_bool(req, 'transparent') or \
            try_to_bool(req, 'embed') or \
            try_to_int(req, 'border', 0, 10000) or \
            try_to_float(req, 'scale', 5.0) or \
            try_to_int(req, 'width', 10, 131072) or \
            try_to_int(req, 'height', 10, 131072) or \
            try_to_bool(req, 'crop')
    if error: return {'error': error}, 400

    source = request.get_data()

    accept = request.accept_mimetypes
    content_types = {
        'image/png': 'png',
        'image/jpeg': 'jpeg',
        'image/svg+xml; charset=utf-8': 'svg',
        'application/pdf': 'pdf'
    }
    best = accept.best_match(content_types.keys())
    if not best in content_types:
        return {'error': f"Not Acceptable; must 'Accept:' one of: {list(content_types.keys())}"}, 406

    fmt = content_types[best]
    return convert_common(req, source, fmt)

if __name__ == '__main__':
    app.run()
