import React from "react";
import { AbsoluteFill, Html5Audio, Img, Sequence, interpolate, spring, staticFile } from "remotion";
import { INTRO, momentoDe, type Escena, type Momento } from "./tipos";

const ROJO = "#d7263d";
const fijo = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Número pseudoaleatorio estable para un frame (mismo resultado en cada render)
const azar = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

export const GLITCH = 10; // frames que dura la falla visual de un giro

// Grano de película: cuatro texturas que se alternan
export const Grano: React.FC<{ frame: number }> = ({ frame }) => (
  <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: 0.16, pointerEvents: "none" }}>
    <Img src={staticFile(`sfx/grano${Math.floor(frame / 2) % 4}.png`)} style={{ width: "100%", height: "100%" }} />
  </AbsoluteFill>
);

// Barras de interferencia de colores (estilo señal de TV que se corta)
export const Barras: React.FC<{ frame: number; t: number }> = ({ frame, t }) => {
  if (t >= GLITCH) return null;
  const fuerza = 1 - t / GLITCH;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: 7 }, (_, k) => {
        const r = azar(frame * 7 + k);
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: (azar(frame + k * 3) - 0.5) * 160,
              top: r * 1920,
              width: 1240,
              height: 8 + azar(frame * 3 + k) * 70,
              background: k % 3 === 0 ? "rgba(255,30,70,.32)" : k % 3 === 1 ? "rgba(0,240,255,.26)" : "rgba(255,255,255,.18)",
              opacity: fuerza,
              mixBlendMode: "screen",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// Franjas de la imagen desplazadas a los lados (la foto "se rompe" un instante)
export const Franjas: React.FC<{ frame: number; t: number; children: React.ReactNode }> = ({ frame, t, children }) => {
  if (t >= GLITCH * 0.7) return null;
  return (
    <>
      {[0, 1, 2].map((k) => {
        const arriba = azar(frame * 5 + k) * 1700;
        const alto = 60 + azar(frame * 9 + k) * 220;
        return (
          <AbsoluteFill
            key={k}
            style={{
              clipPath: `inset(${arriba}px 0 ${Math.max(0, 1920 - arriba - alto)}px 0)`,
              transform: `translateX(${(azar(frame * 11 + k) - 0.5) * 140}px)`,
            }}
          >
            {children}
          </AbsoluteFill>
        );
      })}
    </>
  );
};

// Sacudida de cámara al empezar un giro
export const sacudida = (frame: number, t: number) => {
  if (t >= 14) return { x: 0, y: 0 };
  const f = 1 - t / 14;
  return { x: (azar(frame) - 0.5) * 36 * f, y: (azar(frame + 99) - 0.5) * 36 * f };
};

// El dato clave del giro, en grande
export const TextoPantalla: React.FC<{ texto: string; t: number; dur: number; fps: number; fuente: string }> = ({
  texto,
  t,
  dur,
  fps,
  fuente,
}) => {
  const entra = spring({ frame: t - 4, fps, config: { damping: 10, stiffness: 160 } });
  const sale = interpolate(t, [dur * 0.7, dur * 0.7 + 8], [1, 0], fijo);
  const temblor = t < 16 ? Math.sin(t * 2.7) * (16 - t) * 0.6 : 0;
  const tam = texto.length > 16 ? 96 : texto.length > 10 ? 116 : 140;
  return (
    <div style={{ position: "absolute", top: 560, left: 40, right: 40, textAlign: "center", opacity: sale * Math.min(1, entra * 1.5) }}>
      <div
        style={{
          display: "inline-block",
          fontFamily: fuente,
          fontWeight: 900,
          fontSize: tam,
          lineHeight: 1.05,
          color: "#fff",
          padding: "10px 30px 16px",
          background: "rgba(0,0,0,.55)",
          borderBottom: `10px solid ${ROJO}`,
          textShadow: `4px 0 0 rgba(255,30,70,.7), -4px 0 0 rgba(0,240,255,.5), 0 6px 18px #000`,
          transform: `scale(${0.4 + 0.6 * entra}) translateX(${temblor}px) rotate(${(1 - entra) * -4}deg)`,
        }}
      >
        {texto}
      </div>
    </div>
  );
};

// ---------- Sonido ----------

const VOL_CALMA = 0.14;
const VOL_TENSION = 0.17;
const FUNDIDO = 30;

type Plan = { inicios: number[]; duraciones: number[]; escenas: Escena[]; fin: number; total: number };

// Índice de la escena que suena en el frame f (-1 en la intro)
const escenaEn = (p: Plan, f: number) => {
  if (f < INTRO) return -1;
  let i = 0;
  for (let k = 0; k < p.inicios.length; k++) if (f >= p.inicios[k]) i = k;
  return i;
};

const momento = (p: Plan, i: number): Momento | "intro" => (i < 0 ? "intro" : momentoDe(p.escenas[i], i));

// Volumen de cada capa según el momento de la escena, con fundido entre escenas
const volumenCapa = (p: Plan, f: number, capa: "calma" | "tension" | "latido") => {
  const nivel = (m: Momento | "intro") => {
    if (capa === "calma") return m === "calma" ? VOL_CALMA : 0;
    if (capa === "tension") return m === "tension" || m === "giro" || m === "intro" ? VOL_TENSION : 0;
    return m === "tension" ? 0.4 : 0;
  };
  const i = escenaEn(p, f);
  const ahora = nivel(momento(p, i));
  const antes = nivel(momento(p, i - 1));
  const t = i < 0 ? f : f - p.inicios[i];
  let v = antes + (ahora - antes) * Math.min(1, t / FUNDIDO);
  // Silencio de la música justo en el golpe del giro y vuelve poco a poco
  if (i >= 0 && momento(p, i) === "giro" && capa !== "latido") v *= interpolate(t, [0, 2, 40], [1, 0.15, 1], fijo);
  // Entrada al principio y salida al final del video
  v *= interpolate(f, [0, 12, p.total - 40, p.total], [0, 1, 1, 0], fijo);
  // En el cierre solo queda la música de tensión, más baja
  if (f >= p.fin) v *= capa === "tension" ? 0.8 : 0;
  return v;
};

const Efecto: React.FC<{ archivo: string; desde: number; largo: number; volumen: number }> = ({ archivo, desde, largo, volumen }) =>
  desde < 0 ? null : (
    <Sequence from={desde} durationInFrames={largo}>
      <Html5Audio src={staticFile(`sfx/${archivo}`)} volume={volumen} />
    </Sequence>
  );

export const Sonidos: React.FC<Plan & { fps: number }> = (p) => {
  const { escenas, inicios, fps } = p;
  return (
    <>
      <Html5Audio src={staticFile("sfx/musica_calma.wav")} loop volume={(f) => volumenCapa(p, f, "calma")} />
      <Html5Audio src={staticFile("sfx/musica_tension.wav")} loop volume={(f) => volumenCapa(p, f, "tension")} />
      <Html5Audio src={staticFile("sfx/latido.wav")} loop volume={(f) => volumenCapa(p, f, "latido")} />

      {/* Intro: golpe con interferencia al aparecer el título */}
      <Efecto archivo="golpe.wav" desde={0} largo={3 * fps} volumen={0.8} />
      <Efecto archivo="estatica.wav" desde={0} largo={fps} volumen={0.35} />

      {escenas.map((e, k) => {
        const m = momentoDe(e, k);
        const desde = inicios[k];
        if (m === "giro") {
          return (
            <React.Fragment key={k}>
              {/* La tensión sube 3 s antes y se corta con el golpe */}
              {desde - 3 * fps >= INTRO && <Efecto archivo="subida.wav" desde={desde - 3 * fps} largo={3 * fps} volumen={0.3} />}
              {k > 0 && <Efecto archivo="golpe.wav" desde={desde} largo={3 * fps} volumen={0.75} />}
              {k > 0 && <Efecto archivo="estatica.wav" desde={desde} largo={Math.round(fps * 0.5)} volumen={0.25} />}
            </React.Fragment>
          );
        }
        const cambiaFoto = k > 0 && (escenas[k - 1].foto?.archivo ?? "") !== (e.foto?.archivo ?? "");
        return cambiaFoto ? <Efecto key={k} archivo="whoosh.wav" desde={desde - 4} largo={fps} volumen={0.22} /> : null;
      })}

      {/* Cierre */}
      <Efecto archivo="golpe.wav" desde={p.fin} largo={3 * fps} volumen={0.6} />
    </>
  );
};
