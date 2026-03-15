import sys
import keyboard
import time
# Import des fonctions personnalisées (gestion ports, protocole, reconstruction image)
from trans_arduino import *  # ==========================================

# 1. VARIABLES GLOBALES ET SETUP
# ==========================================

# Conteneurs pour les données reçues
im = ''  # Stockera l'objet image reconstruit (OpenCV)
txt = ''  # Stockera le texte décodé
data_cont = ''  # Conteneur brut pour les données binaires

# Drapeaux d'état (State Flags)
sending = False  # true = Le PC est prêt à envoyer le contenu d'un message (payload)
show_packet = True  # true = Affiche les octets bruts envoyés (mode debug)
receiving = False  # true = Le PC est en attente de données venant de l'Arduino


def show_data_as_text():
    """Tente d'afficher les dernières données brutes reçues sous forme de texte ASCII."""
    try:
        print(data_cont.decode('ascii', errors='ignore'))
    except:
        print("data_cont ne contient aucun \'bytearray\' valide.")


# --- Initialisation de la connexion Série ---

show_ports()  # Affiche la liste des ports COM disponibles (fonction de trans_arduino)

port = input("Veuillez choisir un port : ").strip()  # Sélection utilisateur

device_list = [prt.device for prt in ports_list()]  # Validation de l'entrée

if (not port in device_list):
    print("Le port selectionné n'existe pas ou n'est pas attribué")
    sys.exit()  # Arrêt si port invalide

# Ouverture de la connexion (115200 bauds, timeout lecture 1s)
ser = open_connexion(port, baudrate=115200, timeout=1)
ser.readline()  # Nettoyage du buffer initial (enlève les résidus de boot de l'Arduino)

# ==========================================
# 2. BOUCLE PRINCIPALE (CLI)
# ==========================================
while (True):
    # Prompt utilisateur
    inp = input("Entrer la commande accompagnée du message : ").strip()

    # --- Commandes Système & Affichage ---

    if (inp == '/exit'):
        break  # Quitter le script

    elif (inp == '/showimg'):
        # Tente d'afficher l'image reçue via OpenCV
        try:
            cv2.imshow("Reconstruction", im)
            cv2.waitKey(0)  # Attend une touche pour fermer la fenêtre
            cv2.destroyAllWindows()
        except:
            print("Aucune image ouvrable (variable 'im' vide ou invalide).")

    elif (inp == '/showtxt'):
        print(txt)  # Affiche le dernier texte reçu

    elif (inp == '/showpacket Y'):
        show_packet = True  # Active le mode verbeux (debug hexadécimal)

    elif (inp == '/showpacket N'):
        show_packet = False  # Désactive le mode verbeux

    elif (inp == '/help'):
        # Affiche l'aide (command_list est défini dans trans_arduino.py)
        print()
        for commmand in command_list:
            print(commmand[0], ":", commmand[1])
        print()

    elif (inp == '/clear'):
        print('\n' * 80)  # Simulation de "clear screen"

    elif (inp == '/show_data_as_text'): #permet de voir les caractères mal interprétés
        show_data_as_text()

    elif (inp == '/showports'):
        show_ports()

    # --- Gestion Dynamique du Port Série ---

    elif (inp.split(' ')[0] == '/setport' and len(inp.split(' ')) == 2):
        new_port = inp.split(' ')[1]
        device_list = [prt.device for prt in ports_list()]

        if (new_port in device_list):
            print("Changement du port en - " + new_port)
            close_connexion(ser)  # Ferme l'ancienne connexion proprement
            # Ouvre la nouvelle connexion
            ser = open_connexion(new_port, baudrate=115200, timeout=1)
        else:
            print("Port non reconnu")

    # --- Commandes de Communication Simple ---

    # Commande de test : Vérifie que l'Arduino répond (Ping/Pong)
    elif (inp == '/test'): #permet de rdémarrer
        print("test envoyé")
        ser.write('test'.encode(encoding='ascii', errors='ignore'))
        # Lit la réponse immédiate de l'Arduino
        print(ser.readline().decode(encoding='ascii', errors='ignore'))

        # Commande d'initialisation d'envoi
    elif (inp == '/send'): #initialiser la transmission
        print("transmission initiée")
        # Envoie la commande 'send' pour mettre l'Arduino en mode réception
        ser.write('send'.encode(encoding='ascii', errors='ignore'))
        # L'Arduino doit répondre (ex: "Arduino pret a transmettre")
        print(ser.readline().decode(encoding='ascii', errors='ignore'))
        sending = True  # Active le drapeau pour que la prochaine boucle traite le message

    # --- Commandes de Configuration (Vitesse / Seuil) ---

    # Format attendu : /speed 503 (50*10^3) ou /treshold 214 (2.14V)
    elif ((inp.split(' ')[0] == "/speed" or inp.split(' ')[0] == "/treshold") and len(inp.split(' ')) == 2):
        error_found = False
        try:
            n = inp.split(' ')[1]
            for a in n:
                int(a)  # Validation numérique
        except:
            error_found = True
            print("Aucun nombre approprié en argument")

        if (not error_found):
            # Validation des plages de valeurs
            # Speed : 3 chiffres, exposant (dernier chiffre) <= 3
            # Threshold : <= 330 (3.30V max)
            if (
                    (inp.split(' ')[0] == "/speed" and len(n) == 3 and int(n[2]) <= 3) or
                    (inp.split(' ')[0] == "/treshold" and int(n) <= 330) and len(n) == 3):

                cmd = ""
                if (inp.split(' ')[0] == "/speed"):
                    # Calcul pour affichage utilisateur (ex: 503 -> 50000)
                    speed = int(n[0]) * 10 + int(n[1])
                    speed *= 10 ** int(n[2])
                    print(f"Demande de changement du bitrate à {speed}b/s envoyée")
                    cmd = "s" + n  # Protocole: 's' + 3 chiffres
                else:
                    print(f"Demande de changement de la tension seuil à {int(n) / 100}V envoyée")
                    cmd = "t" + n  # Protocole: 't' + 3 chiffres

                ser.write(cmd.encode(encoding='ascii', errors='ignore'))
                print(ser.readline().decode(encoding='ascii', errors='ignore'))  # Confirmation Arduino
            else:
                print("Le nombre entré n'est pas adéquat ou trop élevé")

    # ==========================================
    # 3. LOGIQUE D'ENVOI DE DONNÉES (SENDING MODE)
    # ==========================================
    # Ce bloc s'exécute si l'utilisateur a tapé '/send' au tour précédent,
    # puis a tapé le message à envoyer.
    elif (sending):
        # Génère l'en-tête (Header) selon le type de message entré (fonction de trans_arduino)
        header, msg = generate_header(inp)

        error_found = False

        # Vérification des types
        if (isinstance(header, bytearray) and isinstance(msg, bytes)):
            print("Header et message générés avec succès")
        else:
            error_found = True
            print(f"Erreur detectée : header est {type(header)} et msg est {type(msg)}")

        if (not error_found):
            print(f"header : {[hex(byte) for byte in header]}")

            if (show_packet):
                print(f"message : {[hex(ms) for ms in msg]}")

            # --- Construction de la Trame ---
            to_trans = bytearray() #tableau contenant tous les bytes
            to_trans.extend(header)  # Ajout Header
            to_trans.extend(msg)  # Ajout Payload
            to_trans.append(255)  # Ajout Byte de Fin (0xFF)

            start = time.perf_counter()

            # Envoie la trame avec gestion du Handshake ('R')
            # L'Arduino envoie 'R' quand il est prêt pour le prochain octet
            send_with_handshake(ser, to_trans)

            # Attend la confirmation finale ("Transmission terminée")
            while (True):
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if line:
                    print(line)
                    break

            sending = False  # Fin de l'envoi
            end = time.perf_counter()
            print(f"Durée de transmission : {(end - start) * 1000:.3f} ms")

            # ==========================================
            # 4. LOGIQUE DE RÉCEPTION (WAITING ANSWER)
            # ==========================================
            # Si l'en-tête indique que nous avons envoyé une requête qui attend une réponse
            # (Codes 248 ou 204), on passe en mode écoute.
            if (header[1] == 248 or header[1] == 204):
                receiving = True

                # Variables d'état pour la reconstruction du paquet
                num_taken = False  # Taille payload connue ?
                first_val_taken = False  # Premier octet validé ?
                pack_count = 0
                n_lsb = 0
                n_msb = 0
                n_payload = 0
                data = bytearray()
                last_receive_time = None

                ser.timeout = 0.1  # Timeout court pour permettre la détection de 'Esc'

                while receiving:
                    # Permet d'interrompre la réception manuellement
                    if keyboard.is_pressed('esc'):
                        print("Sortie du mode écoute.")
                        ser.timeout = 1
                        break

                    c = ser.read(1)  # Lecture octet par octet

                    if c:
                        val = int.from_bytes(c, 'big')  # 'big' ou 'little' sans importance pour 1 octet
                        data.append(val)

                        # Gestion des codes spéciaux reçus
                        if (data[0] == 9):
                            print("100ms écoulées : Timeout côté Arduino.")
                            receiving = False
                        elif (data[0] == 128 and not first_val_taken):
                            print("Reception en cours (Start detected).")
                            first_val_taken = True

                        print(f"data {len(data)} :", hex(val))

                        last_receive_time = time.time()

                        # --- Analyse de l'En-tête de Réponse ---
                        # Une fois 5 octets reçus, on connait la taille du message
                        if (len(data) > 4 and not num_taken):
                            n_lsb = data[2]
                            n_msb = data[3]
                            n_payload = n_msb * 256 + n_lsb
                            print("Taille payload attendue :", n_payload)
                            num_taken = True

                        # --- Fin de Réception ---
                        # Si on a reçu Header (4) + Payload (n) + 1 (pour sécu ou stop)
                        if (len(data) > 4 + n_payload and num_taken):
                            # Traitement selon le type de réponse (2ème octet)
                            if (data[1] == 0xaa):  # 0xAA = Code pour Image
                                im = process_packet(data)  # Reconstruction image
                            elif (data[1] == 0x8f):  # 0x8F = Code pour Texte
                                txt = process_packet(data)  # Décodage texte
                            else:
                                process_packet(data)  # Autre traitement générique
                                data_cont = data
                            break  # Sortie boucle réception

                    else:
                        # --- Gestion Timeout Logiciel (PC) ---
                        if receiving and last_receive_time is not None:
                            elapsed = time.time() - last_receive_time
                            # Si rien reçu depuis 1 seconde alors qu'on attendait la suite
                            if elapsed > 1:
                                # Tentative de sauvetage : on remplit avec des 0
                                if num_taken and len(data) < n_payload + 5:
                                    print(f"Timeout: remplissage avec {n_payload + 5 - len(data)} zéros.")
                                    while len(data) < n_payload + 5:
                                        data.append(0x00)

                                    # On tente de traiter le paquet reconstruit
                                    receiving = False
                                    if data[1] == 0xaa:
                                        im = process_packet(data)
                                    elif data[1] == 0x8f:
                                        txt = process_packet(data)
                                    else:
                                        process_packet(data)
                                        data_cont = data
                                break

                # Commande de sécurité : Reset de l'Arduino
                ser.write('stop'.encode(encoding='ascii', errors='ignore'))
                ser.readall()  # Vide le buffer

    else:
        print("Commande non reconnue ou tentative d'envoi sans '/send' préalable.")

# Fermeture propre
close_connexion(ser)