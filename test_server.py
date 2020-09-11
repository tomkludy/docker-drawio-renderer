import requests, re, io, struct, os

SERVER_ADDRESS="http://drawio-renderer:5000"

valid_content_types = {
    'png': 'image/png',
    'jpeg': 'image/jpeg',
    'svg': 'image/svg+xml; charset=utf-8',
    'pdf': 'application/pdf',
}

with open('test_assets/test_input.drawio', 'r') as file:
    TEST_INPUT = file.read()

def expect_error_lambda(f, expected = 400):
    response = f()
    assert response.status_code == expected
    assert response.headers['content-type'] == 'application/json'
    rj = response.json()
    assert 'error' in rj

def expect_error(json):
    # Try the JSON API
    expect_error_lambda(lambda:
        requests.post(f"{SERVER_ADDRESS}/convert", json = json))

    # Try the upload API
    # first, drop the source/format properties, as they are replaced
    # by the request body and the 'Accept' header in the upload API
    source = json['source'].encode('utf-8') if 'source' in json else b''
    del json['source']
    fmt = json.pop('format', 'png')
    content_type = valid_content_types[fmt] if fmt in valid_content_types else 'nonsense'

    # now, make the request with the remaining stuff as query params
    expect_error_lambda(lambda:
        requests.post(f"{SERVER_ADDRESS}/convert_file",
            params=json, data = source,
            headers = {'accept': content_type}),
            400 if fmt in valid_content_types else 406)

def pdf_content(content):
    # PDFs contain Creator/Producer/CreationDate/ModDate lines
    # which won't match, exclude those from comparison
    content = re.sub(rb'\/Creator\s*\(.*\)', b'', content)
    content = re.sub(rb'\/Producer\s*\(.*\)', b'', content)
    content = re.sub(rb'\/CreationDate\s*\(.*\)', b'', content)
    content = re.sub(rb'\/ModDate\s*\(.*\)', b'', content)
    return content

def jpeg_content(content):
    reader = io.BytesIO(content)
    assert reader.read(2) == b"\xff\xd8"
    while True:
        marker,length = struct.unpack(">2H", reader.read(4))
        assert marker & 0xff00 == 0xff00
        if marker == 0xFFDA: # Start of stream
            return reader.read()
        else:
            reader.seek(length - 2, os.SEEK_CUR)

def expect_file_common(response, file_name, content_type):
    assert response.status_code == 200
    assert response.headers['content-type'] == content_type
    with open(file_name, 'rb') as file:
        expected = file.read()
        actual = response.content

        if content_type == 'application/pdf':
            # Comparing PDFs is generally quite complicated; most sources
            # recommend converting to another image format and then
            # comparing that instead.  For now the test will just strip
            # metadata from the PDF and then do a binary comparison of
            # the rest.  This might turn out to be fragile, so if this
            # test becomes problematic the more heavyweight approach
            # may need to be added later.
            expected = pdf_content(expected)
            actual = pdf_content(actual)
        
        if content_type == 'image/jpeg':
            # Comparing jpegs is complicated because the metadata
            # contains timestamps.
            expected = jpeg_content(expected)
            actual = jpeg_content(actual)

        assert expected == actual

def expect_file(json, file_name):
    # Try the JSON API
    fmt = json['format'] if 'format' in json else 'png'
    content_type = valid_content_types[fmt]
    response = requests.post(f"{SERVER_ADDRESS}/convert", json = json)
    expect_file_common(response, file_name, content_type)

    # Try the upload API
    # first, drop the source/format properties, as they are replaced
    # by the request body and the 'Accept' header in the upload API
    source = json['source'].encode('utf-8')
    del json['source']
    json.pop('format', None)

    # now, make the request with the remaining stuff as query params
    response = requests.post(f"{SERVER_ADDRESS}/convert_file",
                params=json, data = source,
                headers = {'accept': content_type})
    expect_file_common(response, file_name, content_type)

    
def test_get_docs_check_status_equals_200():
    response = requests.get(f"{SERVER_ADDRESS}/docs")
    assert response.status_code == 200

def test_not_json_status_equals_400():
    expect_error_lambda(lambda:
        requests.post(f"{SERVER_ADDRESS}/convert", data = "nonsense!"))

def test_fake_json_status_equals_400():
    expect_error_lambda(lambda:
        requests.post(f"{SERVER_ADDRESS}/convert",
            data = "nonsense!",
            headers = {
                'content-type':'application/json'
            }))

def test_bad_format_status_equals_400_or_406():
    expect_error({
        'source': TEST_INPUT,
        'format': 'nonsense!'
    })

def test_defaults():
    expect_file({
        'source': TEST_INPUT
    }, 'test_assets/png_default.png')

def test_png_defaults():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
    }, 'test_assets/png_default.png')

def test_jpeg_defaults():
    expect_file({
        'source': TEST_INPUT,
        'format': 'jpeg',
    }, 'test_assets/jpeg_default.jpeg')

def test_svg_defaults():
    expect_file({
        'source': TEST_INPUT,
        'format': 'svg',
    }, 'test_assets/svg_default.svg')

def test_pdf_defaults():
    expect_file({
        'source': TEST_INPUT,
        'format': 'pdf',
    }, 'test_assets/pdf_default.pdf')

def test_jpeg_quality_0():
    expect_error({
        'source': TEST_INPUT,
        'format': 'jpeg',
        'quality': 0,
    })

def test_jpeg_quality_1():
    expect_file({
        'source': TEST_INPUT,
        'format': 'jpeg',
        'quality': 1,
    }, 'test_assets/jpeg_quality_1.jpeg')

def test_jpeg_quality_100():
    expect_file({
        'source': TEST_INPUT,
        'format': 'jpeg',
        'quality': 100,
    }, 'test_assets/jpeg_quality_100.jpeg')

def test_jpeg_quality_101():
    expect_error({
        'source': TEST_INPUT,
        'format': 'jpeg',
        'quality': 101,
    })

def test_png_transparent():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'transparent': True,
    }, 'test_assets/png_transparent.png')

def test_png_embed():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'embed': True,
    }, 'test_assets/png_embed.png')

def test_png_border_neg1():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'border': -1,
    })

def test_png_border_100():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'border': 100,
    }, 'test_assets/png_border_100.png')

def test_png_border_10001():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'border': 10001,
    })

def test_png_scale_0():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'scale': 0,
    })

def test_png_scale_point5():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'scale': 0.5,
    }, 'test_assets/png_scale_point5.png')

def test_png_scale_5():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'scale': 5.0,
    }, 'test_assets/png_scale_5.png')

def test_png_scale_5point1():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'scale': 5.1,
    })

def test_png_width_9():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'width': 9,
    })

def test_png_width_10():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'width': 10,
    }, 'test_assets/png_width_10.png')

def test_png_width_1000():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'width': 1000,
    }, 'test_assets/png_width_1000.png')

def test_png_width_1000000():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'width': 1000000,
    })

def test_png_height_9():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'height': 9,
    })

def test_png_height_10():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'height': 10,
    }, 'test_assets/png_height_10.png')

def test_png_height_1000():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'height': 1000,
    }, 'test_assets/png_height_1000.png')

def test_png_height_1000000():
    expect_error({
        'source': TEST_INPUT,
        'format': 'png',
        'height': 1000000,
    })

def test_png_width_400_height_200():
    expect_file({
        'source': TEST_INPUT,
        'format': 'png',
        'width': 400,
        'height': 200,
    }, 'test_assets/png_width_400_height_200.png')

def test_pdf_crop():
    expect_file({
        'source': TEST_INPUT,
        'format': 'pdf',
        'crop': True,
    }, 'test_assets/pdf_crop.pdf')
