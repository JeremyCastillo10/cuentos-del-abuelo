import React from "react";
import {
  AbsoluteFill,
  Easing,
  Html5Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as cargarTitulo } from "@remotion/google-fonts/Creepster";
import { loadFont as cargarTexto } from "@remotion/google-fonts/Montserrat";
import { Siluetas } from "./Siluetas";
import { CUENTA, INTRO, NOMBRE, PALETA, type Ambiente, type Escena, type HistoriaProps } from "./tipos";

const { fontFamily: fuenteTitulo } = cargarTitulo("normal", { weights: ["400"], subsets: ["latin"] });
const { fontFamily: fuenteTexto } = cargarTexto("normal", { weights: ["800", "900"], subsets: ["latin"] });

const ROJO = "#d7263d";
const sombra = "0 4px 0 #000, 0 0 18px rgba(0,0,0,.95), 0 0 40px rgba(0,0,0,.8)";

// Estrellas fijas (misma posición en todos los frames)
const ESTRELLAS = Array.from({ length: 70 }, (_, i) => ({
  x: (i * 389) % 1080,
  y: (i * 211) % 900,
  r: 1 + (i % 3),
  fase: i * 1.7,
}));

const Cielo: React.FC<{ ambiente: Ambiente; frame: number; t: number; luz: number }> = ({ ambiente, frame, t, luz }) => {
  const p = PALETA[ambiente];
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${p.arriba} 0%, ${p.abajo} 75%)` }} />
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        {ESTRELLAS.map((e, i) => (
          <circle key={i} cx={e.x} cy={e.y} r={e.r} fill="#fff" opacity={0.25 + 0.35 * Math.abs(Math.sin(frame / 25 + e.fase))} />
        ))}
        {/* Luna con halo */}
        <circle cx={780} cy={380} r={230} fill={p.niebla} opacity={0.08} />
        <circle cx={780} cy={380} r={120} fill="#e9e6d8" opacity={0.85} />
        <circle cx={820} cy={350} r={110} fill={p.arriba} opacity={0.55} />
        <Siluetas ambiente={ambiente} t={t} luz={luz} />
      </svg>
    </AbsoluteFill>
  );
};

// Bancos de niebla que se desplazan despacio
const Niebla: React.FC<{ color: string; frame: number }> = ({ color, frame }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    {[0, 1, 2, 3].map((i) => {
      const x = ((frame * (0.6 + i * 0.25) + i * 400) % 1800) - 600;
      return (
        <div
          key={i}
          style={{
            position: "absolute",
            left: x,
            top: 1150 + i * 150,
            width: 1100,
            height: 260,
            // Degradado radial en vez de blur: se ve parecido y es mucho más rápido de renderizar
            background: `radial-gradient(ellipse at center, ${color} 0%, transparent 70%)`,
            opacity: 0.16 + (i % 2) * 0.06,
          }}
        />
      );
    })}
  </AbsoluteFill>
);

// Foto real a pantalla completa, oscurecida para dar ambiente de misterio
const Foto: React.FC<{ archivo: string }> = ({ archivo }) => (
  <AbsoluteFill>
    <Img
      src={staticFile(archivo)}
      // El oscurecido ya viene hecho de scripts/imagenes.py (más rápido que un filtro CSS por fotograma)
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
    {/* Tinte frío y oscuro arriba y abajo para que el texto se lea */}
    <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(5,8,20,.55) 0%, rgba(5,8,20,.15) 35%, rgba(5,8,20,.2) 60%, rgba(0,0,0,.75) 100%)" }} />
  </AbsoluteFill>
);

// Fondo de una escena: su foto si la hay; si no, el escenario dibujado
const Fondo: React.FC<{ escena: Escena; frame: number; luz: number }> = ({ escena, frame, luz }) =>
  escena.foto ? <Foto archivo={escena.foto.archivo} /> : <Cielo ambiente={escena.ambiente} frame={frame} t={frame} luz={luz} />;

export const Historia: React.FC<HistoriaProps> = ({ episodio, duraciones }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  if (!episodio) return null;
  const { escenas } = episodio;

  const inicios: number[] = [];
  let acc = INTRO;
  for (const d of duraciones) {
    inicios.push(acc);
    acc += d;
  }
  let i = 0;
  for (let k = 0; k < escenas.length; k++) if (frame >= inicios[k]) i = k;
  const enIntro = frame < INTRO;
  const enOutro = frame >= acc;
  const escena = escenas[i];
  const t = frame - (inicios[i] ?? 0);
  const dur = duraciones[i] ?? 1;

  // Fundido entre lugares cuando cambia el ambiente
  const previa = i > 0 ? escenas[i - 1] : escena;
  const claveFondo = (e: Escena) => e.foto?.archivo ?? e.ambiente;
  const cambio = !enIntro && claveFondo(previa) !== claveFondo(escena);
  const mezcla = cambio ? interpolate(t, [0, 24], [0, 1], { extrapolateRight: "clamp" }) : 1;

  // Relámpago breve al entrar en un lugar nuevo
  // Solo cuando cambia el lugar (no en cada foto), para no cansar
  const cambioLugar = !enIntro && previa.ambiente !== escena.ambiente;
  const relampago = cambioLugar ? interpolate(t, [0, 2, 5, 7, 12], [0, 0.45, 0.08, 0.28, 0], { extrapolateRight: "clamp" }) : 0;
  // Luces de ventanas que parpadean de vez en cuando
  const luz = Math.sin(frame / 3) > 0.92 ? 0.2 : 0.85 + 0.15 * Math.sin(frame / 11);

  // Acercamiento lento durante cada escena
  const zoom = interpolate(t, [0, dur], [1.04, 1.1], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });

  // Subtítulos: las palabras se van iluminando al ritmo de la narración
  const palabras = escena.texto.split(" ");
  const visibles = Math.ceil(interpolate(t, [0, dur * 0.9], [0, palabras.length], { extrapolateRight: "clamp" }));
  // Subtítulo por tramos de 8 palabras: solo se ve la frase que se está diciendo
  const TRAMO = 8;
  const tramo = Math.min(Math.floor(Math.max(0, visibles - 1) / TRAMO), Math.floor((palabras.length - 1) / TRAMO));
  const desde = tramo * TRAMO;
  const enPantalla = palabras.slice(desde, desde + TRAMO);

  const entraTitulo = spring({ frame, fps, config: { damping: 9 } });
  const temblor = enIntro ? Math.sin(frame * 2.1) * 3 : 0;
  const salidaIntro = interpolate(frame, [INTRO - 10, INTRO], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tOutro = frame - acc;
  const musica = interpolate(frame, [0, 20, durationInFrames - 40, durationInFrames], [0, 0.22, 0.22, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", fontFamily: fuenteTexto, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${zoom})` }}>
        {/* La foto anterior solo se dibuja mientras dura el fundido */}
        {mezcla < 1 && <Fondo escena={previa} frame={frame} luz={luz} />}
        <AbsoluteFill style={{ opacity: mezcla }}>
          <Fondo escena={escena} frame={frame} luz={luz} />
        </AbsoluteFill>
        <Niebla color={PALETA[escena.ambiente].niebla} frame={frame} />
      </AbsoluteFill>

      {/* Viñeta y relámpago */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, transparent 35%, rgba(0,0,0,.85) 100%)" }} />
      <AbsoluteFill style={{ background: "#dfe8ff", opacity: relampago }} />

      {/* Crédito de la foto (Pexels/Pixabay no lo exigen, pero se agradece) */}
      {!enIntro && !enOutro && escena.foto && (
        <div style={{ position: "absolute", bottom: 70, left: 50, color: "rgba(255,255,255,.55)", fontSize: 22, fontWeight: 800 }}>
          Foto: {escena.foto.autor} · {escena.foto.fuente}
        </div>
      )}

      {/* Marca arriba */}
      <div style={{ position: "absolute", top: 110, left: 0, right: 0, textAlign: "center" }}>
        <div style={{ display: "inline-block", color: "#e8e2d6", fontWeight: 900, fontSize: 34, letterSpacing: 8, textShadow: sombra }}>
          {NOMBRE}
        </div>
        <div style={{ width: 120, height: 5, background: ROJO, margin: "14px auto 0" }} />
      </div>

      {/* Tarjeta de título */}
      {enIntro && (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: salidaIntro, background: "rgba(0,0,0,.45)" }}>
          <div
            style={{
              fontFamily: fuenteTitulo,
              color: ROJO,
              fontSize: 128,
              lineHeight: 1.05,
              textAlign: "center",
              padding: "0 70px",
              textShadow: "0 0 30px rgba(215,38,61,.6), 0 6px 0 #000",
              transform: `scale(${0.6 + 0.4 * entraTitulo}) translateX(${temblor}px)`,
            }}
          >
            {episodio.titulo}
          </div>
        </AbsoluteFill>
      )}

      {/* Subtítulos */}
      {!enIntro && !enOutro && (
        <div style={{ position: "absolute", left: 70, right: 70, top: 1180, textAlign: "center" }}>
          <div style={{ color: "#fff", fontWeight: 900, fontSize: 74, lineHeight: 1.2, textShadow: sombra }}>
            {enPantalla.map((p, j) => {
              const k = desde + j;
              return (
                <span key={k} style={{ opacity: k < visibles ? 1 : 0.3, color: k === visibles - 1 ? "#ffd6d6" : "#fff" }}>
                  {p}{" "}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Cierre */}
      {enOutro && (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", background: "rgba(0,0,0,.55)" }}>
          <div style={{ transform: `scale(${spring({ frame: tOutro, fps, config: { damping: 11 } })})`, textAlign: "center" }}>
            <div style={{ fontFamily: fuenteTitulo, color: ROJO, fontSize: 110, textShadow: sombra }}>¿Te dio miedo?</div>
            <div style={{ color: "#fff", fontWeight: 900, fontSize: 56, marginTop: 30, textShadow: sombra }}>
              Síguenos para más historias
            </div>
            <div style={{ display: "inline-block", marginTop: 34, background: ROJO, color: "#fff", fontWeight: 900, fontSize: 52, padding: "12px 34px", borderRadius: 14 }}>
              {CUENTA}
            </div>
          </div>
        </AbsoluteFill>
      )}

      <Html5Audio src={staticFile("musica.wav")} loop volume={musica} />
      {escenas.map((e, k) => {
        if (!e.audio) return null;
        // Con Gemini un audio cubre todo su grupo de escenas
        const largo =
          e.grupo === undefined
            ? duraciones[k]
            : escenas.reduce((a, x, j) => (x.grupo === e.grupo ? a + duraciones[j] : a), 0);
        return (
          <Sequence key={k} from={inicios[k]} durationInFrames={largo}>
            <Html5Audio
              src={staticFile(e.audio)}
              volume={(f) =>
                interpolate(f, [0, 3, largo - 3, largo], [0, 1, 1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              }
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
