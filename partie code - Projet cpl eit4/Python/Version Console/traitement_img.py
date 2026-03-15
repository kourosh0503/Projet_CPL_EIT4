import numpy as np
import cv2

def bgr_to_rgb(img_bgr):
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

def rgb_to_bgr(img_rgb):
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

def nearest_color_index(rgb, palette):
    diff = palette.astype(np.int16) - rgb.astype(np.int16)
    d2 = np.sum(diff * diff, axis=1)
    return int(np.argmin(d2))


def build_palette_and_indices(img_rgb, max_colors=256, merge_tolerance=0):
    # 1. Aplatir l'image pour avoir une simple liste de pixels
    # K-Means dans OpenCV demande des données de type float32
    Z = img_rgb.reshape((-1, 3))
    Z = np.float32(Z)

    # 2. Définir les critères d'arrêt de l'algorithme
    # On s'arrête après 10 itérations ou si la précision atteint 1.0
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

    # 3. Exécuter l'algorithme K-Means
    # KMEANS_PP_CENTERS est une méthode intelligente pour placer les couleurs initiales
    ret, labels, centers = cv2.kmeans(Z, max_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)

    # 4. Construire la palette
    # Les 'centers' sont nos 256 couleurs dominantes. On les repasse en entiers.
    centers = np.uint8(centers)
    palette = centers.tolist()

    # 5. Reconstruire la matrice des indices
    # Les 'labels' contiennent l'index (de 0 à 255) pour chaque pixel.
    H, W, _ = img_rgb.shape
    indices = labels.flatten().reshape((H, W))

    # On s'assure du bon type de données pour ta fonction de sérialisation
    indices = indices.astype(np.uint8 if max_colors <= 256 else np.uint16)

    return palette, indices

def ensure_palette_256(palette):
    out = [list(map(int, c)) for c in palette]
    if len(out) == 0:
        out.append([0, 0, 0])
    while len(out) < 256:
        out.append(out[-1] if len(out) > 0 else [0, 0, 0])
    return out[:256]

def serialize_img_packet(palette256, indices):
    H, W = indices.shape  # (hauteur, largeur)
    if not (1 <= W <= 255 and 1 <= H <= 255):
        raise ValueError("Dimensions hors limites: L et H doivent être dans [1..255].")
    packet = bytearray()
    if len(palette256) != 256:
        raise ValueError("La palette doit contenir exactement 256 couleurs.")
    for (R, G, B) in palette256:
        packet.extend([int(R) & 0xFF, int(G) & 0xFF, int(B) & 0xFF])
    if indices.dtype != np.uint8:
        indices = indices.astype(np.uint8, copy=False)
    packet.extend(indices.flatten().tolist())
    return bytes(packet)


def encode_image(img, merge_tolerance=0, max_colors=256, out_path=None):

    palette, indices = build_palette_and_indices(img, max_colors=max_colors, merge_tolerance=merge_tolerance)
    palette256 = ensure_palette_256(palette)
    packet = serialize_img_packet(palette256, indices)
    H, W = indices.shape
    if out_path:
        with open(out_path, "wb") as f:
            f.write(packet)
    return {
        "shapeLH": img.shape[0:2][::-1],
        "packet": packet
    }

def rebuild_img(img_enc):
    l = img_enc["shapeLH"][0]
    h = img_enc["shapeLH"][1]

    img_cnst = np.zeros((h,l,3),dtype=np.uint8)

    palette = []

    for i in range(0,256*3,3):
        palette.append(list(img_enc["packet"][i:i+3]))

    index = img_enc["packet"][768:]

    for i,ind in enumerate(index):
        h_pos = i // l
        l_pos = i % l
        img_cnst[h_pos,l_pos] = palette[ind]

    img_cnst = rgb_to_bgr(img_cnst)
    return img_cnst

#Image à envoyer en cas d'erreur
def image_erreur_remplacement(width=200, height=200, square_size=20):
    # Crée une image blanche (RGB)
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Coordonnées du carré rouge centré
    x1 = (width - square_size) // 2
    y1 = (height - square_size) // 2
    x2 = x1 + square_size
    y2 = y1 + square_size

    # Dessine le carré rouge
    img[y1:y2, x1:x2] = [0, 0, 255]

    return img


"""
#Cette partie de code est là pour tester les différentes fonctions

im_name = input("Entrer le nom de l'image : ").strip()
im = cv2.imread("images\\" + im_name)
im = bgr_to_rgb(im)

cv2.imshow(im_name,rebuild_img(encode_image(im)))
cv2.waitKey(0)
cv2.destroyAllWindows()


cv2.imshow("test",image_erreur_remplacement())
cv2.waitKey(0)
cv2.destroyAllWindows()
"""
