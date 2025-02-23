import base64

icon_data = """
AAABAAEAQEAAAAEAIAAoQgAAFgAAACgAAABAAAAAgAAAAAEAIAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAA
[... 这里是很长的 Base64 编码，为了简洁省略 ...]
"""

with open('resources/icon.ico', 'wb') as f:
    f.write(base64.b64decode(icon_data)) 