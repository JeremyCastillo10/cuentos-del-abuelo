import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { loadFont as cargarTitulo } from "@remotion/google-fonts/Creepster";
import { loadFont as cargarTexto } from "@remotion/google-fonts/Montserrat";
import { NOMBRE, type Episodio } from "./tipos";

const { fontFamily: fuenteTitulo } = cargarTitulo("normal", { weights: ["400"], subsets: ["latin"] });
const { fontFamily: fuenteTexto } = cargarTexto("normal", { weights: ["800", "900"], subsets: ["latin"] });

const ROJO = "#d7263d";
const AMARILLO = "#ffd23f";

// Miniatura del video (1080x1920). El texto va en el centro, que es lo que queda visible
// cuando Facebook la recorta a 4:5 en el feed.
export const Portada: React.FC<{ episodio: Episodio | null }> = ({ episodio }) => {
  if (!episodio) return null;
  const foto = episodio.portada_foto ?? episodio.escenas.find((e) => e.foto)?.foto?.archivo;
  const frase = (episodio.portada ?? episodio.titulo).toUpperCase();
  const palabras = frase.split(" ");
  // La última palabra (o las dos últimas si son cortas) en amarillo: es la que más llama la atención
  const resaltar = palabras.length > 2 && palabras[palabras.length - 1].length < 5 ? 2 : 1;
  const normal = palabras.slice(0, palabras.length - resaltar).join(" ");
  const fuerte = palabras.slice(palabras.length - resaltar).join(" ");
  const tam = frase.length > 18 ? 150 : frase.length > 11 ? 175 : 205;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", fontFamily: fuenteTexto }}>
      {foto && (
        <Img src={staticFile(foto)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "brightness(1.35) contrast(1.15)" }} />
      )}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,.1) 20%, rgba(0,0,0,.85) 100%)" }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(120,0,15,.35) 0%, transparent 30%, transparent 70%, rgba(120,0,15,.45) 100%)" }} />

      {/* Sello "CASO REAL" */}
      <div style={{ position: "absolute", top: 470, left: 0, right: 0, textAlign: "center" }}>
        <span
          style={{
            display: "inline-block", background: ROJO, color: "#fff", fontWeight: 900, fontSize: 54,
            letterSpacing: 6, padding: "10px 34px", transform: "rotate(-3deg)", boxShadow: "0 8px 30px rgba(0,0,0,.7)",
          }}
        >
          CASO REAL
        </span>
      </div>

      {/* Frase grande */}
      <div style={{ position: "absolute", top: 620, left: 50, right: 50, textAlign: "center" }}>
        <div
          style={{
            fontWeight: 900, fontSize: tam, lineHeight: 1.0, color: "#fff", letterSpacing: -2,
            textShadow: "0 10px 0 #000, 0 0 40px rgba(0,0,0,.9), 6px 0 0 rgba(215,38,61,.8)",
            WebkitTextStroke: "4px #000",
          }}
        >
          {normal && <div>{normal}</div>}
          <div style={{ color: AMARILLO }}>{fuerte}</div>
        </div>
      </div>

      {/* Título de la historia, más pequeño */}
      <div
        style={{
          position: "absolute", top: 1330, left: 70, right: 70, textAlign: "center",
          fontFamily: fuenteTitulo, color: ROJO, fontSize: 76, lineHeight: 1.05,
          textShadow: "0 0 24px rgba(215,38,61,.6), 0 5px 0 #000",
        }}
      >
        {episodio.titulo}
      </div>

      {/* Marca */}
      <div style={{ position: "absolute", bottom: 120, left: 0, right: 0, textAlign: "center", color: "#e8e2d6", fontWeight: 900, fontSize: 34, letterSpacing: 8, textShadow: "0 3px 12px #000" }}>
        {NOMBRE}
      </div>
    </AbsoluteFill>
  );
};
