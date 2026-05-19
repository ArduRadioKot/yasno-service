
  # Современный UI/UX для EdTech

  This is a code bundle for Современный UI/UX для EdTech. The original project is available at https://www.figma.com/design/ulpTzaIgyK3orwpd1L3dsS/%D0%A1%D0%BE%D0%B2%D1%80%D0%B5%D0%BC%D0%B5%D0%BD%D0%BD%D1%8B%D0%B9-UI-UX-%D0%B4%D0%BB%D1%8F-EdTech.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.

  ## Backend Setup

  To enable AI features (test generation and AI chat), you need to set up the OpenRouter API key:

  1. Get an API key from [OpenRouter](https://openrouter.ai/)
  2. Copy `backend/.env.example` to `backend/.env`
  3. Add your API key: `OPENROUTER_API_KEY=your_key_here`
  4. Run the backend: `npm run backend`

  The backend uses Gemma 4b model via OpenRouter for:
  - Generating 3-question tests when clicking "Начать занятие" in AI recommendations
  - AI-powered chat responses in the chat screen

  If no API key is configured, the app falls back to rule-based responses.