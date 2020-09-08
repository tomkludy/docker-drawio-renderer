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
import os, subprocess, re, shutil

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

@app.route('/convert', methods=['POST'])
@expects_json(schema, fill_defaults=True)
def convert():
    req = g.data
    fmt = req['format']
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
        with open(infile, "w") as tmp:
            tmp.write(req['source'])

        cmd = ['xvfb-run', '/usr/bin/drawio', '-x', '-f', fmt, '-o', outfile]
        if 'quality' in req:
            cmd.extend(['-q', str(req['quality'])])
        if 'transparent' in req:
            cmd.append('-t')
        if 'embed' in req:
            cmd.append('-e')
        if 'border' in req:
            cmd.extend(['-b', str(req['border'])])
        if 'scale' in req:
            cmd.extend(['-s', str(req['scale'])])
        if 'width' in req:
            cmd.extend(['--width', str(req['width'])])
        if 'height' in req:
            cmd.extend(['--height', str(req['height'])])
        if 'crop' in req:
            cmd.append('--crop')

        # this must be the next-to-last parameter
        cmd.append(infile)

        # this must be the last parameter
        cmd.append('--no-sandbox')

        # xvfb-run /usr/bin/drawio -x -f png \"\${@}\" --no-sandbox
        tries_remaining = 3
        while tries_remaining > 0:
            result = subprocess.run(cmd, universal_newlines=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

            # occasionally, this error happens.  Trying again should fix it
            # "xvfb-run: error: Xvfb failed to start"
            if len(result.stderr) > 0:
                error = result.stderr.splitlines()[0]
                if tries_remaining > 0:
                    if error == 'xvfb-run: error: Xvfb failed to start':
                        tries_remaining = tries_remaining - 1
                        continue
                return {'message': f'Error executing draw.io: {error}'}, 400
            
            break

        line = result.stdout.splitlines()[0]
        if f" -> {outfile}" not in line:
            return {'message': f'Error processing input: {line}'}, 400

        return send_file(outfile, attachment_filename=outbase)
    finally:
        os.umask(saved_umask)
        shutil.rmtree(tmpdir)

if __name__ == '__main__':
    app.run()