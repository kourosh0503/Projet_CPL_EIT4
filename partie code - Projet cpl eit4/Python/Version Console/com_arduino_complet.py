import sys
import keyboard
from trans_arduino import *  # Import des fonctions personnalisées de communication avec Arduino

#Initialisation du conteneur de l'image et du texte
im = ''
txt = ''
data_cont = ''

def show_data_as_text():
    try:
        print(data_cont.decode('ascii', errors='ignore'))
    except:
        print("data_cont ne contient aucun \'bytearray\'")

sending = False  # Booléen indiquant si on est en phase d'envoi de données
show_packet = True  # Booléen pour afficher ou non le contenu des paquets envoyés
receiving = False

show_ports()  # Affiche la liste des ports série disponibles

port = input("Veuillez choisir un port : ").strip()  # Demande à l'utilisateur de choisir un port série

device_list = [prt.device for prt in ports_list()]  # Liste des noms de ports disponibles

if(not port in device_list):
    print("Le port selectionné n'existe pas ou n'est pas attribué")
    sys.exit()  # Quitte le programme si le port choisi n'est pas valide

ser = open_connexion(port,baudrate=115200,timeout=1)  # Ouvre la connexion série avec les paramètres spécifiés
ser.readline()  # Vide le buffer du Arduino (lit la première ligne éventuelle)

# Boucle principale du programme
while(True):
    inp = input("Entrer la commande accompagnée du message : ").strip()  # Lecture de la commande utilisateur

    # Commande pour arrêter la communication et quitter le programme
    if(inp == '/exit'):
        break

        # Affiche l'image reçue si disponible
    elif (inp == '/showimg'):
        try:
            h, w = im.shape[:2]
            im_upscaled = cv2.resize(im, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST)
            cv2.imshow("Image Finale Complète (Upscale x3)", im_upscaled)
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
            print(commmand[0], ":",commmand[1])
        print()

    # Efface l'écran (simulé par plusieurs sauts de ligne)
    elif (inp == '/clear'):
        print('\n'*80)

    elif (inp == '/show_data_as_text'):
        show_data_as_text()

    # Affiche à nouveau la liste des ports disponibles
    elif(inp == '/showports'):
        show_ports()

    # Changer le port série utilisé (ex: /setport COM3 ou /setport /dev/ttyUSB0)
    elif(inp.split(' ')[0] == '/setport' and len(inp.split(' ')) == 2):
        device_list = [prt.device for prt in ports_list()]
        if(inp.split(' ')[1] in device_list):
            print("Changement du port en - " + inp.split(' ')[1])
            close_connexion(ser)  # Ferme la connexion série précédente
            ser = open_connexion(inp.split(' ')[1], baudrate=115200, timeout=1)  # Ouvre la nouvelle connexion
        else:
            print("Port non reconnu")

    # Commande pour tester la connexion Arduino en envoyant "test" et affichant la réponse
    elif(inp == '/test'):
        print("test envoyé")
        ser.write('test'.encode(encoding='ascii',errors='ignore'))  # Envoie la commande test
        print(ser.readline().decode(encoding='ascii',errors='ignore'))  # Affiche la réponse reçue

    # Commande pour démarrer la transmission de données
    elif(inp == '/send'):
        print("transmission initiée")
        ser.write('send'.encode(encoding='ascii', errors='ignore'))  # Envoie la commande 'send' à Arduino
        print(ser.readline().decode(encoding='ascii',errors='ignore'))  # Affiche la réponse Arduino
        sending = True  # Passe en mode envoi

    # Commandes pour changer la vitesse (bitrate) ou le seuil (tension)
    elif((inp.split(' ')[0] == "/speed" or inp.split(' ')[0] == "/treshold") and len(inp.split(' ')) == 2):
        error_found = False
        try:
            n = inp.split(' ')[1]
            for a in n:
                int(a)  # Vérifie que chaque caractère est un chiffre
        except:
            error_found = True
            print("Aucun nombre approprié en argument")

        if(not error_found):
            if(
                (inp.split(' ')[0] == "/speed" and len(n) == 3 and int(n[2]) <= 3) or
                (inp.split(' ')[0] == "/treshold" and int(n) <= 330) and len(n) == 3):
                # Décodage de la vitesse selon un format spécifique (2 chiffres + exposant)
                if(inp.split(' ')[0] == "/speed"):
                    speed = int(n[0]) * 10 + int(n[1])
                    speed *= 10**int(n[2])
                    print(f"Demande de changement du bitrate à {speed}b/s envoyée")
                    cmd = "s" + n
                else:
                    print(f"Demande de changement de la tension seuil à {int(n)/100}V envoyée")
                    cmd = "t" + n

                ser.write(cmd.encode(encoding='ascii', errors='ignore'))
                print(ser.readline().decode(encoding='ascii', errors='ignore'))
            else:
                print("Le nombre entré n'est pas adéquat ou trop élevé")

    # Si la commande /send a été envoyée précédemment, on envoie ici le message saisi
    elif(sending):
        header,msg = generate_header(inp)  # Génère l'en-tête et le message à envoyer

        error_found = False

        # Vérifie que header est un bytearray et msg est un bytes
        if(isinstance(header,bytearray) and isinstance(msg,bytes)):
            print("Header et message générés avec succès")
        else:
            error_found = True
            print(f"Erreure detectée : header est {type(header)} et msg est {type(msg)}")

        if(not error_found):
            print(f"header : {[hex(byte) for byte in header]}")  # Affiche l'en-tête en hexadécimal

            if(show_packet):
                print(f"message : {[hex(ms) for ms in msg]}")  # Affiche le message en hexadécimal

            # Combine header + message + un octet 0xFF pour terminer la trame

            to_trans = bytearray()
            to_trans.extend(header)
            to_trans.extend(msg)
            to_trans.append(255)

            start = time.perf_counter()  # Démarre le chronomètre

            send_with_handshake(ser,to_trans)

            # Attend la réponse de l'Arduino
            while(True):
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if line:
                    print(line)  # Affiche la réponse reçue
                    break
            sending = False  # Fin de l'envoi
            end = time.perf_counter()  # Stop le chronomètre
            print(f"Durée de transmission : {(end - start)*1000:.3f} ms")  # Affiche le temps en ms

            # Si l'en-tête correspond à certains codes, on attend une autre réponse
            if(header[1] == 248 or header[1] == 204):
                receiving = True
                num_taken = False  # Indique si la taille du payload a été lue
                first_val_taken = False
                pack_count = 0
                n_lsb = 0
                n_msb = 0
                n_payload = 0
                data = bytearray()
                last_receive_time = None  # Temps de la dernière réception (pour timeout)
                ser.timeout = 0.1  # Timeout de lecture court pour ne pas bloquer trop longtemps

                while receiving:
                    # Sortie du mode écoute si touche 'Esc' pressée
                    if keyboard.is_pressed('esc'):
                        print("Sortie du mode écoute.")
                        ser.timeout = 1
                        break

                    c = ser.read(1)  # Lecture d'un octet

                    if c:
                        data.append(int.from_bytes(c))  # Ajoute l'octet reçu

                        if (data[0] == 9):
                            print("100ms écoulées : Timeout.")
                            receiving = False
                        elif (data[0] == 128 and not first_val_taken):
                            print("Reception en cours.")
                            first_val_taken = True

                        print(f"data {len(data)} :", hex(int.from_bytes(c)))

                        last_receive_time = time.time()  # Met à jour le temps de réception

                        # Lecture de la taille du payload (après avoir reçu les 4 premiers octets)
                        if (len(data) > 4 and not num_taken):
                            n_lsb = data[2]
                            n_msb = data[3]
                            n_payload = n_msb * 256 + n_lsb
                            print("num taken :", n_payload)
                            num_taken = True

                        # Quand le paquet complet est reçu, traitement selon le type
                        if (len(data) > 4 + n_payload and num_taken):
                            if (data[1] == 0xaa):  # Image
                                im = process_packet(data)
                            elif (data[1] == 0x8f):  # Texte
                                txt = process_packet(data)
                            else:
                                process_packet(data)
                                data_cont = data
                            break

                    else:
                        # Si pas de données reçues, vérifie le timeout de réception
                        if receiving and last_receive_time is not None:
                            elapsed = time.time() - last_receive_time
                            if elapsed > 1:  # Timeout après 1 seconde sans réception
                                # Si paquet incomplet, on complète avec des zéros
                                if num_taken and len(data) < n_payload + 5:
                                    print(f"Timeout: remplissage avec {n_payload + 5 - len(data)} zéros.")
                                    while len(data) < n_payload + 5:
                                        data.append(0x00)

                                    # Traitement final du paquet complété
                                    receiving = False
                                    if data[1] == 0xaa:
                                        im = process_packet(data)
                                    elif data[1] == 0x8f:
                                        txt = process_packet(data)
                                    else:
                                        process_packet(data)
                                        data_cont = data
                                break
                ser.write('stop'.encode(encoding='ascii', errors='ignore'))
                ser.readall()

    else:
        print("Commande non reconnue ou tentative d'envoi sans '/send' préalable.")

# Ferme la connexion série proprement avant de quitter
close_connexion(ser)