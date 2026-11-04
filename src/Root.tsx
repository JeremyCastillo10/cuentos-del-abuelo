import React from "react";
import { Composition, staticFile, type CalculateMetadataFunction } from "remotion";
import { getAudioData } from "@remotion/media-utils";
import { Historia } from "./Historia";
import { FPS, INTRO, OUTRO, PAUSA, type Episodio, type HistoriaProps } from "./tipos";

const calcularMetadata: CalculateMetadataFunction<HistoriaProps> = async ({ props }) => {
  const episodio: Episodio =
    props.episodio ?? (await fetch(staticFile("episodio.json")).then((r) => r.json()));
  const duraciones: number[] = new Array(episodio.escenas.length).fill(0);
  const escenas = episodio.escenas;
  for (let i = 0; i < escenas.length; i++) {
    const e = escenas[i];
    if (e.grupo !== undefined) {
      // Trozo de Gemini: el audio de la primera escena cubre todo el grupo y se reparte por palabras
      if (!e.audio) continue;
      const indices = escenas.map((x, k) => (x.grupo === e.grupo ? k : -1)).filter((k) => k >= 0);
      const datos = await getAudioData(staticFile(e.audio));
      const total = datos.durationInSeconds * FPS;
      const palabras = indices.reduce((a, k) => a + (escenas[k].palabras ?? 1), 0);
      let usado = 0;
      indices.forEach((k, j) => {
        const parte = j === indices.length - 1 ? Math.ceil(total) - usado : Math.round((total * (escenas[k].palabras ?? 1)) / palabras);
        duraciones[k] = parte;
        usado += parte;
      });
      duraciones[indices[indices.length - 1]] += PAUSA;
    } else if (e.audio) {
      const datos = await getAudioData(staticFile(e.audio));
      duraciones[i] = Math.ceil(datos.durationInSeconds * FPS) + PAUSA;
    } else {
      // Sin audio (vista previa): tiempo aproximado según las palabras
      duraciones[i] = Math.ceil((e.texto.split(" ").length / 2.5) * FPS) + PAUSA;
    }
  }
  return {
    durationInFrames: INTRO + duraciones.reduce((a, b) => a + b, 0) + OUTRO,
    props: { episodio, duraciones },
  };
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Historia"
    component={Historia}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={300}
    defaultProps={{ episodio: null, duraciones: [] }}
    calculateMetadata={calcularMetadata}
  />
);
