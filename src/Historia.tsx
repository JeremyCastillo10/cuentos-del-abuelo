import React from "react";
import {
  AbsoluteFill,
  Easing,
  Html5Audio,
  Img,
  Loop,
  OffthreadVideo,
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
import { CUENTA, INTRO, NOMBRE, PALETA, momentoDe, type Ambiente, type Escena, type HistoriaProps } from "./tipos";
import { Barras, Franjas, Grano, Sonidos, TextoPantalla, sacudida } from "./Efectos";

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

// Video de archivo a pantalla completa, algo más lento (más cinematográfico) y en bucle si la escena es larga
const VELOCIDAD_VIDEO = 0.85;
const Video: React.FC<{ archivo: string; segundos: number; fps: number }> = ({ archivo, segundos, fps }) => (
  <AbsoluteFill>
    <Loop durationInFrames={Math.max(24, Math.floor((segundos * fps) / VELOCIDAD_VIDEO) - 2)} layout="none">
      <OffthreadVideo src={staticFile(archivo)} muted playbackRate={VELOCIDAD_VIDEO} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </Loop>
    <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(5,8,20,.55) 0%, rgba(5,8,20,.15) 35%, rgba(5,8,20,.2) 60%, rgba(0,0,0,.75) 100%)" }} />
  </AbsoluteFill>
);

// Fondo de una escena: su video, su foto o, si no hay, el escenario dibujado.
// "desde" es el frame en que empieza ese medio (si varias escenas seguidas lo comparten, sigue sin cortes).
const Fondo: React.FC<{ escena: Escena; frame: number; luz: number; desde: number; fps: number }> = ({ escena, frame, luz, desde, fps }) => {
  if (escena.video)
    return (
      <Sequence from={desde} layout="none">
        <Video archivo={escena.video.archivo} segundos={escena.video.segundos} fps={fps} />
      </Sequence>
    );
  return escena.foto ? <Foto archivo={escena.foto.archivo} /> : <Cielo ambiente={escena.ambiente} frame={frame} t={frame} luz={luz} />;
};

const medioDe = (e: Escena) => e.video?.archivo ?? e.foto?.archivo ?? e.ambiente;

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
  const claveFondo = medioDe;
  // Primer frame del medio de una escena (escenas seguidas con el mismo video lo continúan)
  const desdeMedio = (k: number) => {
    let j = k;
    while (j > 0 && medioDe(escenas[j - 1]) === medioDe(escenas[k])) j--;
    return inicios[j] ?? 0;
  };
  const cambio = !enIntro && claveFondo(previa) !== claveFondo(escena);
  const mezcla = cambio ? interpolate(t, [0, 24], [0, 1], { extrapolateRight: "clamp" }) : 1;

  // Relámpago breve al entrar en un lugar nuevo
  // Solo cuando cambia el lugar (no en cada foto), para no cansar
  const cambioLugar = !enIntro && previa.ambiente !== escena.ambiente;
  const relampago = cambioLugar ? interpolate(t, [0, 2, 5, 7, 12], [0, 0.45, 0.08, 0.28, 0], { extrapolateRight: "clamp" }) : 0;
  // Luces de ventanas que parpadean de vez en cuando
  const luz = Math.sin(frame / 3) > 0.92 ? 0.2 : 0.85 + 0.15 * Math.sin(frame / 11);

  const momento = momentoDe(escena, i);
  const esGiro = !enIntro && !enOutro && momento === "giro";
  // Acercamiento lento con paneo, alternando la dirección en cada escena; en los giros, un golpe de zoom
  const avance = interpolate(t, [0, dur], [0, 1], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });
  const golpeZoom = esGiro ? interpolate(t, [0, 12], [0.1, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }) : 0;
  const zoom = 1.06 + 0.08 * avance + golpeZoom;
  const lado = i % 2 === 0 ? 1 : -1;
  const panX = lado * interpolate(avance, [0, 1], [-28, 28]);
  const panY = interpolate(avance, [0, 1], [i % 3 === 0 ? 18 : -18, i % 3 === 0 ? -18 : 18]);
  const golpe = esGiro ? sacudida(frame, t) : { x: 0, y: 0 };
  const destello = esGiro && i > 0 ? interpolate(t, [0, 1, 4], [0.55, 0.35, 0], { extrapolateRight: "clamp" }) : 0;
  const oscuro = momento === "tension" ? 0.25 : 0;

  // Subtítulos: las palabras se van iluminando al ritmo de la narración
  const palabras = escena.texto.split(" ");
  const visibles = Math.ceil(interpolate(t, [0, dur * 0.9], [0, palabras.length], { extrapolateRight: "clamp" }));
  // Subtítulo por tramos de 8 palabras: solo se ve la frase que se está diciendo
  const TRAMO = 8;
  const tramo = Math.min(Math.floor(Math.max(0, visibles - 1) / TRAMO), Math.floor((palabras.length - 1) / TRAMO));
  const desde = tramo * TRAMO;
  const enPantalla = palabras.slice(desde, desde + TRAMO);

  const tOutro = frame - acc;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", fontFamily: fuenteTexto, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${panX + golpe.x}px, ${panY + golpe.y}px) scale(${zoom})` }}>
        {/* La foto anterior solo se dibuja mientras dura el fundido */}
        {mezcla < 1 && <Fondo escena={previa} frame={frame} luz={luz} desde={desdeMedio(Math.max(0, i - 1))} fps={fps} />}
        <AbsoluteFill style={{ opacity: mezcla }}>
          <Fondo escena={escena} frame={frame} luz={luz} desde={desdeMedio(i)} fps={fps} />
        </AbsoluteFill>
        {esGiro && i > 0 && (
          <Franjas frame={frame} t={t}>
            <Fondo escena={escena} frame={frame} luz={luz} desde={desdeMedio(i)} fps={fps} />
          </Franjas>
        )}
        <Niebla color={PALETA[escena.ambiente].niebla} frame={frame} />
      </AbsoluteFill>

      {/* Viñeta y relámpago */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, transparent 35%, rgba(0,0,0,.85) 100%)" }} />
      <AbsoluteFill style={{ background: "#dfe8ff", opacity: relampago }} />
      <AbsoluteFill style={{ background: "#000", opacity: oscuro }} />
      <Grano frame={frame} />
      {esGiro && i > 0 && <Barras frame={frame} t={t} />}
      <AbsoluteFill style={{ background: "#fff", opacity: destello, mixBlendMode: "overlay" }} />
      {enIntro && <Barras frame={frame} t={frame % 30} />}
      {esGiro && escena.pantalla && <TextoPantalla texto={escena.pantalla} t={t} dur={dur} fps={fps} fuente={fuenteTexto} />}

      {/* Crédito de la foto (Pexels/Pixabay no lo exigen, pero se agradece) */}
      {!enIntro && !enOutro && (escena.video || escena.foto) && (
        <div style={{ position: "absolute", bottom: 70, left: 50, color: "rgba(255,255,255,.55)", fontSize: 22, fontWeight: 800 }}>
          {escena.video ? "Video" : "Foto"}: {(escena.video ?? escena.foto)!.autor} · {(escena.video ?? escena.foto)!.fuente}
        </div>
      )}

      {/* Título sobre la primera escena (la narración ya empezó: no se hace esperar a nadie) */}
      {!enIntro && i === 0 && (
        <div
          style={{
            position: "absolute", top: 230, left: 50, right: 50, textAlign: "center",
            fontFamily: fuenteTitulo, color: ROJO, fontSize: 82, lineHeight: 1.05,
            textShadow: "0 0 24px rgba(215,38,61,.6), 0 5px 0 #000",
            opacity: interpolate(t, [0, 6, dur - 10, dur], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            transform: `scale(${0.8 + 0.2 * spring({ frame: t, fps, config: { damping: 12 } })})`,
          }}
        >
          {episodio.titulo}
        </div>
      )}

      {/* Marca arriba */}
      <div style={{ position: "absolute", top: 110, left: 0, right: 0, textAlign: "center" }}>
        <div style={{ display: "inline-block", color: "#e8e2d6", fontWeight: 900, fontSize: 34, letterSpacing: 8, textShadow: sombra }}>
          {NOMBRE}
        </div>
        <div style={{ width: 120, height: 5, background: ROJO, margin: "14px auto 0" }} />
      </div>

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

      <Sonidos escenas={escenas} inicios={inicios} duraciones={duraciones} fin={acc} total={durationInFrames} fps={fps} />
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
