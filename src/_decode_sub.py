import base64
raw = open("sub_raw.txt", "r", encoding="utf-8").read().strip()
# try standard base64 (may have url-safe or padding issues)
def try_decode(s):
    try:
        return base64.b64decode(s + '=' * (-len(s) % 4))
    except Exception as e:
        return None
dec = try_decode(raw)
if dec is None:
    try:
        dec = base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4))
    except Exception as e:
        print("decode fail", e); raise
text = dec.decode('utf-8', errors='replace')
print("DECODED LEN", len(text))
print("HEAD 800:")
print(text[:800])
open("sub_decoded.yaml", "w", encoding="utf-8").write(text)
print("saved sub_decoded.yaml")
