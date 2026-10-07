import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyBEHZmGI-ox6UI43j-T221CVHlbU-RAiLo",
    authDomain: "hireshield-ai-ddcab.firebaseapp.com",
    projectId: "hireshield-ai-ddcab",
    storageBucket: "hireshield-ai-ddcab.firebasestorage.app",
    messagingSenderId: "41616589276",
    appId: "1:41616589276:web:2972b247ece889fc4c4f19",
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);