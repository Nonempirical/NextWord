# Installationsguide för NextWord (Windows)

Denna guide hjälper dig att installera och köra NextWord-projektet på Windows från början, även om du inte har någon tidigare erfarenhet.

## Steg 1: Hämta projektet från GitHub

### Alternativ A: Ladda ner som ZIP-fil
1. Gå till projektets GitHub-sida
2. Klicka på den gröna knappen "Code" (eller "Kod" om sidan är på svenska)
3. Välj "Download ZIP"
4. Extrahera ZIP-filen till en mapp på din dator (t.ex. `Skrivbord` eller `Dokument`)
5. Högerklicka på ZIP-filen och välj "Extrahera alla..." eller använd WinRAR/7-Zip

### Alternativ B: Använd Git (om du har Git installerat)
1. Öppna PowerShell eller Command Prompt
   - Tryck `Windows + R`, skriv `powershell` och tryck Enter
   - Eller sök efter "PowerShell" i Start-menyn
2. Navigera till mappen där du vill ha projektet:
   ```powershell
   cd C:\Users\DittAnvändarnamn\Desktop
   ```
   *(Ersätt "DittAnvändarnamn" med ditt Windows-användarnamn)*
3. Klona projektet:
   ```powershell
   git clone <projektets-github-länk>
   ```
4. Gå in i projektmappen:
   ```powershell
   cd NextWord
   ```

---

## Steg 2: Installera Python

Python behövs för att köra backend-servern.

### Kontrollera om Python redan är installerat
1. Öppna PowerShell eller Command Prompt
2. Skriv:
   ```powershell
   python --version
   ```

Om du ser ett versionsnummer (t.ex. "Python 3.9.0" eller högre), har du redan Python installerat. Gå vidare till Steg 3.

### Installera Python om det saknas

1. Gå till https://www.python.org/downloads/
2. Ladda ner den senaste Python 3.x-versionen (klicka på den stora gula knappen)
3. Kör installationsfilen som du laddade ner
4. **VIKTIGT:** Markera rutan "Add Python to PATH" innan du klickar "Install Now"
   - Detta är mycket viktigt! Utan detta kommer kommandona inte att fungera
5. Klicka på "Install Now"
6. Vänta tills installationen är klar
7. Klicka på "Close" när installationen är klar

### Verifiera installationen
1. Stäng och öppna PowerShell/Command Prompt igen (detta är viktigt!)
2. Skriv:
   ```powershell
   python --version
   ```
3. Du bör se ett versionsnummer. Om du ser "Python 3.x.x", är installationen lyckad!

---

## Steg 3: Installera pip (Python Package Manager)

pip installeras automatiskt med Python, men låt oss kontrollera att det fungerar:

1. Öppna PowerShell eller Command Prompt
2. Skriv:
   ```powershell
   python -m pip --version
   ```

Om du ser ett versionsnummer (t.ex. "pip 23.0.1"), fungerar pip korrekt. Om du får ett felmeddelande, installera om Python och se till att markera "Add Python to PATH".

---

## Steg 4: Installera Node.js och npm

Node.js behövs för att köra frontend-applikationen.

### Kontrollera om Node.js redan är installerat
1. Öppna PowerShell eller Command Prompt
2. Skriv:
   ```powershell
   node --version
   npm --version
   ```

Om du ser versionsnummer för båda, har du redan Node.js installerat. Gå vidare till Steg 5.

### Installera Node.js om det saknas

1. Gå till https://nodejs.org/
2. Ladda ner LTS-versionen (Long Term Support - den gröna knappen, rekommenderas)
3. Kör installationsfilen som du laddade ner
4. Följ installationsguiden (klicka "Next" på alla steg, standardinställningar fungerar bra)
5. När installationen är klar, stäng och öppna PowerShell/Command Prompt igen
6. Verifiera installationen:
   ```powershell
   node --version
   npm --version
   ```
7. Du bör se versionsnummer för båda kommandona

---

## Steg 5: Installera Python-beroenden

1. Öppna PowerShell eller Command Prompt
2. Navigera till projektmappen. Om du laddade ner ZIP-filen till Skrivbordet:
   ```powershell
   cd C:\Users\DittAnvändarnamn\Desktop\NextWord
   ```
   *(Ersätt "DittAnvändarnamn" med ditt Windows-användarnamn)*
   
   **Tips:** Du kan också högerklicka på projektmappen i Utforskaren, välj "Öppna i Terminal" eller "Öppna PowerShell-fönster här".

3. Installera beroendena:
   ```powershell
   python -m pip install -r requirements.txt
   ```

Detta kan ta flera minuter (5-15 minuter) eftersom det laddar ner PyTorch och andra stora paket. Du kommer att se mycket text scrolla förbi - det är normalt! Vänta tills installationen är klar och du ser kommandotolken igen.

**Tips:** Om du får felmeddelanden om behörigheter:
- Stäng PowerShell/Command Prompt
- Högerklicka på PowerShell/Command Prompt i Start-menyn
- Välj "Kör som administratör"
- Försök igen

---

## Steg 6: Installera Node.js-beroenden

Medan du fortfarande är i projektmappen i PowerShell/Command Prompt:

```powershell
npm install
```

Detta installerar React, Vite och andra frontend-beroenden. Det kan ta några minuter (2-5 minuter). Vänta tills installationen är klar.

---

## Steg 7: Verifiera installationen

Kontrollera att allt är installerat korrekt:

### Python-paket
I PowerShell/Command Prompt, skriv:
```powershell
python -m pip list | findstr fastapi
```

Du bör se `fastapi` i listan tillsammans med ett versionsnummer.

### Node-paket
```powershell
npm list --depth=0
```

Du bör se `react`, `vite` och andra paket listade.

---

## Steg 8: Starta projektet

Nu är allt installerat! Här är hur du startar projektet:

### Starta Backend (PowerShell/Command Prompt #1)

1. Öppna ett PowerShell- eller Command Prompt-fönster
2. Navigera till projektmappen:
   ```powershell
   cd C:\Users\DittAnvändarnamn\Desktop\NextWord
   ```
3. Starta backend-servern:
   ```powershell
   python -m uvicorn main:app --reload
   ```

Du bör se meddelandet "Loaded model: Qwen/Qwen2.5-1.5B" när modellen har laddats. Låt detta fönster vara öppet - stäng det inte!

**OBS:** Första gången kan det ta lite längre tid (flera minuter) eftersom modellen laddas ner från HuggingFace. Du behöver internetanslutning för detta.

### Starta Frontend (PowerShell/Command Prompt #2)

1. Öppna ett **nytt** PowerShell- eller Command Prompt-fönster
   - Du kan öppna ett nytt genom att högerklicka på PowerShell/Command Prompt i Start-menyn
   - Eller trycka `Windows + R`, skriv `powershell` och tryck Enter igen
2. Navigera till projektmappen igen:
   ```powershell
   cd C:\Users\DittAnvändarnamn\Desktop\NextWord
   ```
3. Starta frontend-servern:
   ```powershell
   npm run dev
   ```

Du bör se ett meddelande om att servern körs på `http://localhost:3000` eller `http://localhost:3001`.

**VIKTIGT:** Du behöver ha **båda** fönstren öppna samtidigt - ett för backend och ett för frontend!

---

## Steg 9: Öppna applikationen

1. Öppna din webbläsare (Chrome, Firefox, Edge, etc.)
2. Gå till adressfältet och skriv: `http://localhost:3000` eller `http://localhost:3001`
   - (Använd det nummer som visas i frontend-terminalfönstret)
3. Tryck Enter
4. Du bör nu se NextWord-gränssnittet!

---

## Felsökning

### "python: command not found" eller "python känns inte igen"
- Kontrollera att du installerade Python korrekt
- Kontrollera att du markerade "Add Python to PATH" under installationen
- Stäng och öppna PowerShell/Command Prompt igen
- Om det fortfarande inte fungerar, installera om Python och se till att markera "Add Python to PATH"

### "pip: command not found" eller "pip känns inte igen"
Prova:
```powershell
python -m pip install -r requirements.txt
```

### "npm: command not found" eller "npm känns inte igen"
- Kontrollera att Node.js är korrekt installerat:
  ```powershell
  node --version
  ```
- Om det inte fungerar, installera om Node.js från https://nodejs.org/
- Stäng och öppna PowerShell/Command Prompt igen efter installationen

### Port redan används
Om port 8000 eller 3000/3001 redan används:
- Stäng andra program som kan använda dessa portar
- Stäng alla PowerShell/Command Prompt-fönster och starta om
- Om problemet kvarstår, starta om datorn

### Modellen laddas inte
- Kontrollera din internetanslutning (modellen laddas ner första gången)
- Vänta lite längre - första nedladdningen kan ta 5-10 minuter
- Kontrollera att du har tillräckligt med diskutrymme (modellen är ~3GB)
- Om det tar för lång tid, kontrollera din internetanslutning och försök igen

### CORS-fel i webbläsaren
- Kontrollera att backend körs på port 8000 (se första terminalfönstret)
- Kontrollera att frontend körs på port 3000/3001 (se andra terminalfönstret)
- Se till att båda terminalfönstren är öppna och körs
- Försök uppdatera webbläsarsidan (F5)

### "Access Denied" eller behörighetsfel
- Stäng PowerShell/Command Prompt
- Högerklicka på PowerShell/Command Prompt i Start-menyn
- Välj "Kör som administratör"
- Försök igen

### Installationen tar för lång tid
- Detta är normalt! PyTorch är ett stort paket (~2GB)
- Se till att du har en stabil internetanslutning
- Låt installationen köra klart - avbryt inte processen

---

## Ytterligare hjälp

Om du stöter på problem:
1. Kontrollera att du följde alla steg ovan
2. Kontrollera att alla versioner är korrekta:
   - Python 3.8 eller högre: `python --version`
   - Node.js LTS: `node --version`
3. Försök installera om beroendena:
   ```powershell
   python -m pip install -r requirements.txt --upgrade
   npm install
   ```
4. Kontrollera projektets GitHub-sida för kända problem
5. Se till att Windows är uppdaterat

---

## Snabbstart (för erfarna användare)

Om du redan har Python och Node.js installerat:

```powershell
# Navigera till projektmappen
cd C:\Users\DittAnvändarnamn\Desktop\NextWord

# Installera Python-beroenden
python -m pip install -r requirements.txt

# Installera Node-beroenden
npm install

# Starta backend (i ett PowerShell-fönster)
python -m uvicorn main:app --reload

# Starta frontend (i ett annat PowerShell-fönster)
npm run dev
```

Öppna sedan `http://localhost:3000` i din webbläsare.

---

## Tips för Windows-användare

- **Använd PowerShell istället för Command Prompt** - det är mer kraftfullt och modernare
- **Högerklicka på mappar** i Utforskaren och välj "Öppna i Terminal" eller "Öppna PowerShell-fönster här" för att snabbt navigera till rätt mapp
- **Håll båda terminalfönstren synliga** så att du kan se om något går fel
- **Kontrollera Windows Defender/Firewall** om du har problem med nätverksanslutningar

---

**Lycka till! 🚀**
