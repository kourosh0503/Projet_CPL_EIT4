const int CHUNK_SIZE = 1; // Tableau appelé à chaque fois qu'on veut créer une trame
byte trame[10] = {0,0,0,0,0,0,0,0,0,1}; 
// → Représente une trame de 10 bits (1 start bit + 8 bits data + 1 bit stop)

// Variables de gestion du temps pour la transmission
unsigned long T_BIT = 20; // Période d’un bit en microsecondes (20 µs = 50 kbit/s)

// Entrées et sorties
int ctrl_out = 4; // Broche utilisée pour envoyer la trame
// États et booléens pour gérer l’état de la sortie
byte ctrl_out_state = LOW;

// Tableau contenant la commande reçue depuis le PC
int com[10];
int com_index = 0; // Index de remplissage du tableau de commande

// Variables de contrôle de la transmission
bool transmitting = false;             // Indique si une transmission est en cours
unsigned long t_no_content = 0;        // Compteur de temps sans contenu transmis

// Variables pour gérer le contenu de la trame et son type
int c_index = 0;   // Index courant dans la trame reçue ou transmise
int com_type = 0;  // Type de commande actuelle

// Variables de gestion d’attente de réponse et timeout
unsigned long t_start_wait_ans = 0; // Temps de début d’attente de réponse

// Compteurs pour la taille du payload (données utiles)
int n_payload = 0; // Nombre total d’octets dans le payload
int n_lsb = 0;     // Octet de poids faible du nombre d’octets
int n_msb = 0;     // Octet de poids fort du nombre d’octets

// ===== Début de la récéption =====

// Variables de contrôle pour l'écoute de la trame
bool receive = true;
bool trans_detected = false;         // Indique si une transmission a été détectée (front descendant)
bool in_trame = false;               // Indique si on est en train de recevoir une trame
unsigned long t_start_bit;
signed long interval_and_state[30];
int ias_ind = 0;
byte two_first_val[2];

//Fonction de lecture rapide pour ne pas avoir de délais
int ctrl_in = 5;                     // Broche d'entrée pour lire la trame
int ctrl_in_state;                   // Variable pour stocker l'état de la broche d'entrée
int pack_count = 0; //Variable de comptage pour savoir où on se situe dans la reception du packet

int trame_index = 0;

inline int fastRead() {
  return (PIOC->PIO_PDSR & (1u << 30-ctrl_in)) ? 1 : 0;
}

// Ajoute l'état actuel de la broche d'entrée à la trame
void add_to_trame(){
  trame[trame_index] = ctrl_in_state; // Stocke état du bit reçu
  trame_index++;                      // Incrémente l'index
}

int decode_trame(){
  trame_index = 0;
  int val = 0;
  for(int i = 1; i < 9; ++i){
    if (trame[i] == 1) {
      val |= (1 << (i - 1));
    }
  }
  return val;
}

bool is_type(int val){
  return (val == 143) || (val == 248) || (val == 170) || (val == 204);
}

// ===== Fin de la récéption =====

// Fonction qui calcule le nombre d’octets dans le payload
void set_n_payload(){
  n_payload = 256 * n_msb + n_lsb; // Combine les deux octets pour obtenir la taille
}

// Fonction puissance entière (équivalent de pow mais sur int)
int pow(int a,int b){
  int n = 1;
  for(int i = 0; i < b; ++i){
    n *= a;
  }
  return n;
}

// Traite la commande envoyée au Arduino et réinitialise le tableau commande
void process_com(){
  com_index = 0; // Réinitialisation de l’index commande

  // Commande "test" → simple vérification
  if(com[0] == 't' && com[1] == 'e' && com[2] == 's' && com[3] == 't'){
    SerialUSB.println("Test effectue : Bernard operationnel.");
  }

  // Commande "tXYZ" → changement du seuil (tension) pour DAC (valeur max 3.30V)
  else if(com[0] == 't' && ((com[1] - '0')*100 +  (com[2] - '0')*10 + (com[3] - '0')) <= 330){
    SerialUSB.print("Seuil change en : ");
    int n = ((com[1] - '0')*100 +  (com[2] - '0')*10 + (com[3] - '0')); // Valeur seuil en centiVolts

    float voltage = n/100.0; // Conversion en volts

    // Conversion voltage en valeur DAC 12 bits (0-4095)
    int dacValue = (int)((voltage) / 3.3 * 4095);  // Ex: 2.14V → ~2656
    analogWrite(DAC1, dacValue);                    // Écrit la valeur sur la sortie DAC1

    char nbr_buffer[10];                             // Buffer pour conversion texte
    itoa(n, nbr_buffer, 10);                         // Conversion int → string
    SerialUSB.print(nbr_buffer);
    SerialUSB.println("cV");
  }

  // Commande l'arrêt du processus d'écoute
  else if(com[0] == 's' && com[1] == 't' && com[2] == 'o' && com[3] == 'p'){
    transmitting = false;

    c_index = 0;

    if(com_type == 248 || com_type == 204){
          c_index = 1;

          transmitting = true;
          digitalWrite(ctrl_out,HIGH);
          ctrl_out_state = HIGH;
          delay(10);

          gen_trame(128);
          transmit_trame();
        }

        trans_detected = false;
        in_trame = false;

        n_payload = 0;
        n_msb = 0;
        n_lsb = 0;
        pack_count = 0;
        com_type = 0;
  }

  // Commande "sXYZ" → modification du bitrate (X,Y,Z sont des chiffres)
  else if(com[0] == 's' && com[1] - '0' <=9 && com[2] - '0' <= 9 && com[3] - '0' <= 9){
    SerialUSB.print("Bitrate change en : ");
    int n = (com[1] - '0')*10 + com[2] - '0'; // Calcule la base du bitrate
    n *= pow(10,com[3] - '0'); // Multiplie selon le dernier chiffre (ex: "s500" = 50000)
    T_BIT = (unsigned long)(1000000/n);         // Convertit bitrate en période (µs)

    char nbr_buffer[10]; // Buffer pour stocker la valeur du bitrate en chaîne de caractères
    itoa(n, nbr_buffer, 10); // Conversion en texte
    SerialUSB.println(nbr_buffer);
  }
}

// Réinitialise la trame à 0 (sauf bit de stop à 1)
void reset_trame(){
  for(int i=0; i<9; ++i){
      trame[i] = 0;
  }
  trame[9] = 1; // Bit de stop
}

// Génère la trame correspondant à la valeur d’un octet
void gen_trame(byte val){
  reset_trame(); // Sécurité
  byte num_s = 1;
  // Convertit la valeur binaire de val dans la trame
  while(val != 0){
    trame[num_s] = (val % 2); // Remplit de droite à gauche
    val /= 2;
    num_s++;
  }
}

// Fonction d’envoi physique de la trame sur la broche ctrl_out
void transmit_trame(){

  if(T_BIT < 150){
    noInterrupts();
  }
  
  unsigned long next_BIT;
  next_BIT = micros(); // Horodatage de départ
  // Envoi séquentiel des 10 bits de la trame
  for(int i=0; i<10; ++i){
    if(trame[i]){
      ctrl_out_state = HIGH;
    } else {
      ctrl_out_state = LOW;
    }
    digitalWrite(ctrl_out, ctrl_out_state); // Écrit l’état du bit sur la broche

    next_BIT += T_BIT; // Planifie le prochain bit

    while(micros() < next_BIT); // Attente du moment exact d’envoi du bit
  }

  if(T_BIT < 150){
    interrupts();
  }

  // Si la transmission s’est terminée (tout le payload envoyé)
  if(c_index == n_payload + 5){
    c_index = 0;
    transmitting = false;
    SerialUSB.println("Transmission terminee.");
  }
  else{  
    SerialUSB.write('R'); //Le arduino signale qu'il est prêt à envoyer le prochain morceau
  }
}

// Fonction setup exécutée une seule fois au démarrage
void setup() {  

  pinMode(LED_BUILTIN, OUTPUT); //Pour debuggage
  digitalWrite(LED_BUILTIN, LOW);

  SerialUSB.begin(115200);        // Initialise la communication USB à 115200 bauds
  while (!SerialUSB);             // Attend que la connexion soit établie
  SerialUSB.println("Arduino USB prêt !");

  pinMode(ctrl_out,OUTPUT);       // Définit la broche de sortie
  pinMode(ctrl_in,INPUT);     // Configure la broche ctrl_in comme entrée

  analogWriteResolution(12);  // Configure la résolution du DAC en 12 bits (0–4095)
  int dacValue = (int)(0.35 / 3.3 * 4095);  // Valeur DAC initiale correspondant à 2.14V
  analogWrite(DAC1, dacValue);               // Écrit cette valeur sur la sortie DAC1
}

int c = 0; // Variable pour stocker le caractère reçu

// Boucle principale
void loop() {

  if(transmitting){
    trans_detected = false;
  }
  else{
    trans_detected = true;
  }

  // Vérifie si un caractère est reçu via USB
  if (SerialUSB.available() > 0){
    c = SerialUSB.read(); // Lit le caractère

    if(transmitting){ // Si une transmission est en cours
      c_index++;

      // Décodage des informations de la trame selon l’index
      switch(c_index){
        case 3:
          n_lsb = c; // Octet faible du payload
          break;
        case 4:
          n_msb = c; // Octet fort du payload
          set_n_payload(); // Calcule la taille totale du payload
          break;
      }

      gen_trame(c);                // Génère la trame du caractère courant
      transmit_trame();            // Transmet la trame
      
      if(transmitting){
        digitalWrite(ctrl_out, HIGH);
      }
      else{
        digitalWrite(ctrl_out,LOW);
      }
    }

    else { // Si on n’est pas en mode transmission → lecture de commande texte
      com[com_index] = c;
      com_index++;

      if(com_index >= 4){ // Quand 4 caractères reçus → commande complète
        process_com();    // Traite la commande
      }
    }
  }

  else if(trans_detected){
    ctrl_in_state = fastRead();
    // Si pas encore dans la trame mais transmission détectée et ligne toujours à LOW
    if(!in_trame && trans_detected && ctrl_in_state == LOW){
      
      if(T_BIT < 150){
        noInterrupts();
      }
      t_start_bit = micros();
      in_trame = true; 
    }

    // Si transmission détectée et en cours de réception
    if(trans_detected && in_trame){
      
      //What the fuck !

      unsigned long t = t_start_bit;
      unsigned long t_first = t_start_bit;
      unsigned long t_end_of_trame = t_start_bit + (unsigned long)(9.3*T_BIT);

      byte current_state;

      while(t <= t_end_of_trame){
        t = micros();
        current_state = fastRead();
        if(current_state != ctrl_in_state || t >= t_end_of_trame){
          interval_and_state[ias_ind++] = ctrl_in_state;
          interval_and_state[ias_ind++] = t - t_first;
          t_first = t;
          ctrl_in_state = current_state;
        }
      }

      interval_and_state[ias_ind++] = -1;
      interval_and_state[ias_ind++] = -1;

      for(int i = 0; interval_and_state[i] != -1; i+=2){
        
        signed long duration = interval_and_state[i+1];
        int bit_num = duration/T_BIT + 
          (interval_and_state[i] == 0)*(duration % T_BIT >= 7*T_BIT/20) +
          (interval_and_state[i] == 1)*(duration % T_BIT >= 12*T_BIT/20);
        
        for(int j = 0; j < bit_num && trame_index < 10; ++j){
          trame[trame_index++] = interval_and_state[i];
        }
      }

      in_trame = false; // Fin de réception de la trame
      
      pack_count++; // Incrémente le compteur de paquets reçus

      int val_data = decode_trame();

      if(T_BIT < 150){
        interrupts();
      }

      switch (pack_count) {
        case 1:
          two_first_val[0] = val_data;
          if(val_data != 128){
            pack_count = 0;
          }
          break;
        case 2:
          two_first_val[1] = val_data;
          if(!is_type(two_first_val[1])){
            pack_count = 0;
          }
          else{
            SerialUSB.write(two_first_val[0]);
            SerialUSB.write(two_first_val[1]);
            com_type = val_data;
          }
          break;
      }

      if(pack_count > 2){
        SerialUSB.write(val_data); // Envoie le byte décodé via USB
      }

      reset_trame(); // Réinitialise la trame pour la prochaine réception
      ias_ind = 0;
    }
  }

  else { //IDLE
    if (!transmitting && !in_trame) {
        digitalWrite(ctrl_out, LOW);
    }
  }
}
