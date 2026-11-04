export type Ambiente =
  | "bosque"
  | "casa"
  | "carretera"
  | "mar"
  | "pueblo"
  | "cementerio"
  | "habitacion"
  | "ciudad";

export type Escena = {
  texto: string;
  ambiente: Ambiente;
  // Búsqueda en inglés para la foto (la escribe scripts/historia.py)
  imagen?: string;
  // Foto real elegida por scripts/imagenes.py (Pexels o Pixabay)
  foto?: { archivo: string; autor: string; fuente: string };
  // Ruta dentro de public/, la escribe scripts/voces.py
  audio?: string;
};

export type Episodio = {
  fecha: string;
  tipo: "leyenda" | "misterio" | "crimen";
  fuente?: { titulo: string; url: string };
  titulo: string;
  escenas: Escena[];
  caption: string;
};

export type HistoriaProps = {
  episodio: Episodio | null;
  // Duración en frames de cada escena
  duraciones: number[];
};

export const NOMBRE = "CUENTOS DEL ABUELO";
export const CUENTA = "@cuentos_delabuelo";
export const FPS = 30;
export const INTRO = 60; // tarjeta de título
export const OUTRO = 75; // "Síguenos"
export const PAUSA = 8; // respiro entre frases

// Color de cada lugar: cielo arriba, cielo abajo y tono de la niebla
export const PALETA: Record<Ambiente, { arriba: string; abajo: string; niebla: string }> = {
  bosque: { arriba: "#05080a", abajo: "#12261c", niebla: "#8fb3a0" },
  casa: { arriba: "#07060c", abajo: "#241a2e", niebla: "#a99bb8" },
  carretera: { arriba: "#04060c", abajo: "#1b2233", niebla: "#9aa6bd" },
  mar: { arriba: "#03070d", abajo: "#0d2433", niebla: "#8fb0c4" },
  pueblo: { arriba: "#0a0705", abajo: "#2a1c12", niebla: "#bba58c" },
  cementerio: { arriba: "#050506", abajo: "#1d1d24", niebla: "#b4b4c2" },
  habitacion: { arriba: "#0b0606", abajo: "#2a1010", niebla: "#c49a90" },
  ciudad: { arriba: "#04040a", abajo: "#16152b", niebla: "#9b98c4" },
};
