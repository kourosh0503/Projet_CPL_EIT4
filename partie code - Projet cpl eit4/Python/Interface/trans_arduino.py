import serial
import serial.tools.list_ports
import time
from traitement_img import *  # Import des fonctions de traitement d'image personnalisées

# Liste des commandes disponibles avec leur description pour l'aide
command_list = [
    ["/exit","Permet d'arrêter la communication entre le PC et le Arduino en sécurité."],
    ["/showports","Affiche tous les ports accessibles."],
    ["/speed","Change le bitrate de la transmission du Arduino."],
    ["/send","Initie l'envoie de données, la prochaine commande doit être une commande de transmission."],
    ["/test","Permet de tester si le Arduino est correctement connecté."],
    ["/TXT","Envoie un texte."],
    ["/TXT_REQ","Demande un texte en particulier."],
    ["/IMG","Envoie une image, prend en paramètre le chemin relatif vers l'image"],
    ["/IMG_REQ","Demande une image en particulier."],
    ["/clear","Premet de vider la console."],
    ["/listen","Met l'appareil en mode écoute."],
    ["/showpacket","Afficher le contenu du packet; Options Y (Oui)/N (Non)"]
]

# Fonction pour ouvrir une connexion série
def open_connexion(port, baudrate=115200, timeout=1):
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)  # Ouvre la connexion série
        time.sleep(1)  # Pause pour laisser l'Arduino redémarrer
        if ser.is_open:
            print(f"Connexion établie sur {ser.portstr} à {baudrate} bauds")
        return ser
    except serial.SerialException as e:
        print(f"Erreur de connexion au port {port} : {e}")
        return None  # Retourne None si la connexion échoue

# Fonction pour fermer proprement une connexion série
def close_connexion(ser):
    if ser and ser.is_open:
        ser.close()
        print("Connexion série fermée")

# Affiche les différents ports USB utilisés et leurs détails
def show_ports():
    for port in serial.tools.list_ports.comports():
        print(port)

# Retourne la liste des ports série disponibles
def ports_list():
    return [port for port in serial.tools.list_ports.comports()]

# Convertit un entier décimal en chaîne hexadécimale (sans 0x)
def dec_to_hexstr(n):
    hex_str = ''
    while(n):
        hex_str += str(hex(n%16))[2]  # Récupère le dernier chiffre hex
        n //= 16
    return hex_str[::-1]  # Inverse la chaîne pour l'ordre correct

# Fonction principale qui génère un en-tête et un message à envoyer
def generate_header(inp):
    """
    Reçoit une chaîne de caractères (le message complet avec commande)

    Retourne un tuple (header, message) où:
    - header est un bytearray contenant SOT / TYPE / N (longueur)
    - message est un bytes ou bytearray avec le contenu à envoyer
    Si l'entrée n'est pas valide, retourne des valeurs d'erreur
    """

    if(not isinstance(inp,str)):
        return "NOT","STR"  # Erreur si l'entrée n'est pas une chaîne

    header = bytearray(b'\x80')  # Start Of Transmission (SOT) fixe en 0x80


    # Gestion des commandes texte
    if (inp.startswith('/TXT ')):
        data_type = 'TXT'
        payload = inp.replace('/TXT ', '')  # Supprime la commande pour garder le message
        header.extend(b'\x8f')  # Code type pour TXT
    elif (inp.startswith('/TXT_REQ ')):
        data_type = 'TXT_REQ'
        payload = inp.replace('/TXT_REQ ', '')
        header.extend(b'\xf8')  # Code type pour TXT_REQ

    # Gestion des images à envoyer
    elif (inp.startswith('/IMG ')):
        data_type = 'IMG'
        payload = inp.replace('/IMG ', '')  # Chemin de l'image sans la commande
        header.extend(b'\xaa')  # Code type pour IMG

        img = cv2.imread(payload)  # Lecture de l'image avec OpenCV

        try:
            img = bgr_to_rgb(img)  # Convertit BGR vers RGB (format attendu)
        except:
            # En cas d'erreur (image non trouvée), envoie une image de remplacement
            img = image_erreur_remplacement()
            img = bgr_to_rgb(img)
            print("Image non trouvée, envoie d'une image de remplacement")

        enc_img = encode_image(img)  # Encode l'image en bytes à envoyer

        l = enc_img["shapeLH"][0]  # Largeur de l'image encodée
        h = enc_img["shapeLH"][1]  # Hauteur de l'image encodée

    # Gestion des demandes d'images
    elif (inp.startswith('/IMG_REQ ')):
        data_type = 'IMG_REQ'
        payload = inp.replace('/IMG_REQ ', '')
        header.extend(b'\xcc')  # Code type pour IMG_REQ

    else:
        return "NO","COMMAND"  # Pas de commande reconnue dans l'entrée

    # Si ce n'est pas une image, calcul de la longueur du message en bytes ASCII
    if(data_type != 'IMG'):
        n_dec = len(payload)
        payload = payload.encode(encoding='ascii',errors='ignore')  # Conversion en bytes ASCII
    else:
        # Pour une image, la taille est calculée avec les paramètres spécifiques
        n_dec = 2+768+l*h  # 2 octets + 768 (probablement palette) + taille image
        payload = enc_img["packet"]  # Packet encodé à envoyer

    # Conversion de la taille n_dec en chaîne hexadécimale sur 4 caractères
    n_hex = dec_to_hexstr(n_dec)
    n_hex = (4 - len(n_hex)) * "0" + n_hex  # Ajoute des zéros en tête pour faire 4 caractères

    # Extraction des octets MSB et LSB (ordre little endian)
    msb = n_hex[0:2]
    msb_byte = bytearray()
    msb_byte.append(int(msb, 16))

    lsb = n_hex[2:4]
    lsb_byte = bytearray()
    lsb_byte.append(int(lsb, 16))

    # Ajout de la longueur dans l'en-tête : LSB puis MSB
    header.extend(lsb_byte)
    header.extend(msb_byte)

    # Pour les images, on ajoute aussi la largeur et la hauteur dans l'en-tête
    if(data_type== 'IMG'):
        header.append(l)
        header.append(h)

    return header,payload  # Retourne l'en-tête et le message (bytes)


def process_packet(packet):
    # Calcul taille du payload en combinant LSB et MSB
    n_payload = packet[2] + 256 * packet[3]

    print("type : ", end='')

    # Extraction du payload (données utiles) du paquet
    payload = packet[4:4 + n_payload]

    # Si type TXT
    if(packet[1] in[0x8f,0xf8,0xcc]):
        if (packet[1] == 0xf8):
            print("TXT_REQ")
        elif(packet[1] == 0xcc):
            print("IMG_REQ")
        else:
            print("TXT")
        payload = bytearray(payload)
        print("Payload size :", n_payload)
        print("Payload preview :", [hex(byte) for byte in payload[:10]])  # Aperçu des 10 premiers octets
        return payload.decode(encoding='ascii', errors='ignore')  # Décodage en ASCII

    elif (packet[1] == 0xaa):
        print("IMG")
        print("L :", payload[0])  # Largeur image
        print("H :", payload[1])  # Hauteur image
        img_enc = {"shapeLH": (payload[0], payload[1]), "packet": payload[2:]}  # Reconstruction du format image
        print("Payload size :", n_payload)
        print("Payload preview :", [hex(byte) for byte in payload[:10]])
        try:
            return rebuild_img(img_enc)  # Appel de la fonction de reconstruction d'image
        except:
            print("L'image n'a pas pu etre reconstruite.")

def send_with_handshake(ser, payload):
    for cara in payload:
        # Attendre strictement le 'R'
        while True:
            r = ser.read(1)
            if r == b'R':
                break
        # Une fois le R reçu → envoyer le byte
        ser.write(bytes([cara]))