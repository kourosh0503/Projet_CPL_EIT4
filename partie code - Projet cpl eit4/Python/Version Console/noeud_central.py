import sys
import time
import keyboard
from trans_arduino import *  # Import des fonctions personnalisées de communication avec Arduino

link = {"IMG": {}, "TXT": {}}

# Initialisation du conteneur de l'image et du texte
im = ''
txt = ''

req = ''
req_type = ''

data_cont = ''


def show_data_as_text():
    try:
        print(data_cont.decode('ascii', errors='ignore'))
    except:
        print("data_cont ne contient aucun \'bytearray\'")


sending = False  # Booléen indiquant si on est en phase d'envoi de données
show_packet = True  # Booléen pour afficher ou non le contenu des paquets envoyés
receiving = False
requesting = False

show_ports()  # Affiche la liste des ports série disponibles

port = input("Veuillez choisir un port : ").strip()  # Demande à l'utilisateur de choisir un port série

device_list = [prt.device for prt in ports_list()]  # Liste des noms de ports disponibles

if (not port in device_list):
    print("Le port selectionné n'existe pas ou n'est pas attribué")
    sys.exit()  # Quitte le programme si le port choisi n'est pas valide

ser = open_connexion(port, baudrate=115200, timeout=1)  # Ouvre la connexion série avec les paramètres spécifiés
ser.readline()

# Boucle principale du programme
while (True):

    if (not receiving):
        inp = input("Entrer la commande accompagnée du message : ").strip()  # Lecture de la commande utilisateur

    # Commande pour arrêter la communication et quitter le programme
    if (inp == '/exit'):
        break

    # Affiche l'image reçue si disponible
    elif (inp == '/showimg'):
        try:
            cv2.imshow("Reconstruction", im)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except:
            print("Aucune image ouvrable.")

    # Affiche le texte reçu
    elif (inp == '/showtxt'):
        print(txt)

    # Activer l'affichage des paquets
    elif (inp == '/showpacket Y'):
        show_packet = True

    # Désactiver l'affichage des paquets
    elif (inp == '/showpacket N'):
        show_packet = False

    # Affiche l'aide avec la liste des commandes disponibles
    elif (inp == '/help'):
        print()
        for commmand in command_list:
            print(commmand[0], ":", commmand[1])
        print()

    # Efface l'écran (simulé par plusieurs sauts de ligne)
    elif (inp == '/clear'):
        print('\n' * 80)

    elif (inp == '/show_data_as_text'):
        show_data_as_text()

    # Affiche à nouveau la liste des ports disponibles
    elif (inp == '/showports'):
        show_ports()

    elif (inp == '/listen'):
        receiving = True
        inp = ''

    # Lie une chaine de caractères à une image ou un texte ET prépare le bytearray
    elif (inp.split(' ')[0] == '/link' and len(inp.split(' ')) >= 4 and (inp.split(' ')[1] in ["IMG", "TXT"])):

        link_type = inp.split(' ')[1]
        link_key = inp.split(' ')[2]

        # Reconstruction du terme relié à la requête
        linked_sentence_or_image = ' '.join(inp.split(' ')[3:])

        print(f"Préparation de la donnée pour le lien '{link_key}'...")

        # On simule une entrée pour le générateur de header
        simulated_inp = f"/{link_type} {linked_sentence_or_image}"
        header, msg = generate_header(simulated_inp)

        # On vérifie que la génération s'est bien passée
        if isinstance(header, bytearray) and isinstance(msg, bytes):
            to_trans = bytearray()
            to_trans.extend(header[1:])  # On retire le premier octet car le Arduino s'en occupe
            to_trans.extend(msg)
            to_trans.append(255)  # Octet de fin

            # On sauvegarde le bytearray prêt à l'envoi au lieu du simple texte
            link[link_type][link_key] = to_trans
            print(f"Le terme \"{link_key}\" a été lié et mis en cache")
        else:
            print(f"Erreur lors de la génération de la trame pour le terme '{link_key}'. Le lien n'a pas été créé.")

    # Changer le port série utilisé
    elif (inp.split(' ')[0] == '/setport' and len(inp.split(' ')) == 2):
        device_list = [prt.device for prt in ports_list()]
        if (inp.split(' ')[1] in device_list):
            print("Changement du port en - " + inp.split(' ')[1])
            close_connexion(ser)
            ser = open_connexion(inp.split(' ')[1], baudrate=115200, timeout=1)
        else:
            print("Port non reconnu")

    # Commande pour tester la connexion Arduino
    elif (inp == '/test'):
        print("test envoyé")
        ser.write('test'.encode(encoding='ascii', errors='ignore'))
        print(ser.readline().decode(encoding='ascii', errors='ignore'))

    # Commandes pour changer la vitesse ou le seuil
    elif ((inp.split(' ')[0] == "/speed" or inp.split(' ')[0] == "/treshold") and len(inp.split(' ')) == 2):
        error_found = False
        try:
            n = inp.split(' ')[1]
            for a in n:
                int(a)
        except:
            error_found = True
            print("Aucun nombre approprié en argument")

        if (not error_found):
            if ((inp.split(' ')[0] == "/speed" and len(n) == 3 and int(n[2]) <= 3) or
                    (inp.split(' ')[0] == "/treshold" and int(n) <= 330) and len(n) == 3):

                if (inp.split(' ')[0] == "/speed"):
                    speed = int(n[0]) * 10 + int(n[1])
                    speed *= 10 ** int(n[2])
                    print(f"Demande de changement du bitrate à {speed}b/s envoyée")
                    cmd = "s" + n
                else:
                    print(f"Demande de changement de la tension seuil à {int(n) / 100}V envoyée")
                    cmd = "t" + n

                ser.write(cmd.encode(encoding='ascii', errors='ignore'))
                print(ser.readline().decode(encoding='ascii', errors='ignore'))
            else:
                print("Le nombre entré n'est pas adéquat ou trop élevé")

    elif (receiving):
        print("Entrée en mode écoute")
        num_taken = False
        first_val_taken = False
        pack_count = 0
        n_lsb = 0
        n_msb = 0
        n_payload = 0
        data = bytearray()
        last_receive_time = None
        ser.timeout = 0.1

        while True:
            if keyboard.is_pressed('esc'):
                print("Sortie du mode écoute.")
                ser.timeout = 1
                receiving = False
                break

            c = ser.read(1)

            if c:
                data.append(int.from_bytes(c))
                if (data[0] != 128 and not first_val_taken):
                    print("Attention : SOT manquant !")
                    first_val_taken = True

                print(f"data {len(data)} :", hex(int.from_bytes(c)))
                last_receive_time = time.time()

                if (len(data) > 4 and not num_taken):
                    n_lsb = data[2]
                    n_msb = data[3]
                    n_payload = n_msb * 256 + n_lsb
                    print("num taken :", n_payload)
                    num_taken = True

                if (len(data) > 4 + n_payload and num_taken):
                    if (data[1] == 0xaa):
                        im = process_packet(data)
                    elif (data[1] == 0x8f):
                        txt = process_packet(data)
                    elif (data[1] in [0xf8, 0xcc]):
                        req = process_packet(data)
                        req_type = data[1]
                        requesting = True
                    else:
                        data_cont = data
                    break

            elif not c and first_val_taken:
                if receiving and last_receive_time is not None:
                    elapsed = time.time() - last_receive_time
                    if elapsed > 1:
                        if num_taken and len(data) < n_payload + 5:
                            print(f"Timeout: remplissage avec {n_payload + 5 - len(data)} zéros.")
                            while len(data) < n_payload + 5:
                                data.append(0x00)

                            if data[1] == 0xaa:
                                im = process_packet(data)
                            elif data[1] == 0x8f:
                                txt = process_packet(data)
                            elif (data[1] in [0xf8, 0xcc]):
                                req = process_packet(data)
                                req_type = data[1]
                                requesting = True
                            else:
                                process_packet(data)
                                data_cont = data
                        break
        ser.write('stop'.encode(encoding='ascii', errors='ignore'))
        print("Reception terminée. Traitement de l'information reçue si nécessaire.")

    else:
        print("Commande non reconnue.")

    # --- SECTION OPTIMISÉE ---
    if (requesting):
        print("transmission initiée")
        to_trans = None

        # Récupération directe du bytearray pré-généré dans le cache
        if req_type == 0xf8 and req in link["TXT"]:
            to_trans = link["TXT"][req]
        elif req_type == 0xcc and req in link["IMG"]:
            to_trans = link["IMG"][req]

        # Si le paquet n'a pas été trouvé en cache, on génère une réponse d'erreur à la volée
        if to_trans is None:
            print("Aucun link trouvé dans le dictionnaire. Génération d'un message d'erreur.")
            err_inp = '/TXT La requete n a pas pu etre traitee'
            header, msg = generate_header(err_inp)
            to_trans = bytearray()
            to_trans.extend(header[1:])
            to_trans.extend(msg)
            to_trans.append(255)

        if show_packet:
            print(f"Trame préparée (Taille: {len(to_trans)}) : {[hex(b) for b in to_trans[:20]]}... (tronqué)")

        start = time.perf_counter()  # Démarre le chronomètre

        send_with_handshake(ser, to_trans)

        # Attend la réponse de l'Arduino
        while (True):
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line:
                print("Réponse Arduino:", line)
                break

        sending = False
        end = time.perf_counter()  # Stop le chronomètre
        print(f"Durée de transmission (hors génération de trame) : {(end - start) * 1000:.3f} ms")

    requesting = False

close_connexion(ser)