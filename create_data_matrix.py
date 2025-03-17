import os
from pylibdmtx.pylibdmtx import encode
from PIL import Image

def generate_datamatrix(data, filename):
    encoded = encode(data.encode('utf-8'))
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    img.save(filename)
    print(f"DataMatrix code saved as {filename}")

def generate_datamatrix_series(prefix, start, end, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    for i in range(start, end + 1):
        data = f"{prefix}{i:05d}"
        filename = os.path.join(folder, f"{data}.png")
        generate_datamatrix(data, filename)

# Example usage
generate_datamatrix_series("EW1U9VKMNHY", 0, 999, "data_matrix")
