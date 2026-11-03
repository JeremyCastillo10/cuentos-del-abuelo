import React from "react";
import { Composition, staticFile, type CalculateMetadataFunction } from "remotion";
import { getAudioData } from "@remotion/media-utils";
import { Historia } from "./Historia";
import { FPS, INTRO, OUTRO, PAUSA, type Episodio, type HistoriaProps } from "./tipos";

const calcularMetadata: CalculateMetadataFunction<HistoriaProps> = async ({ props }) => {
  const episodio: Episodio =
    props.episodio ?? (await fetch(staticFile("episodio.json")).then((r) => r.json()));
  const duraciones: number[] = [];
  for (const e of episodio.escenas) {
    if (e.audio) {
      const datos = await getAudioData(staticFile(e.audio));
      duraciones.push(Math.ceil(datos.durationInSeconds * FPS) + PAUSA);
    } else {
      // Sin audio (vista previa): tiempo aproximado según las palabras
      duraciones.push(Math.ceil((e.texto.split(" ").length / 2.5) * FPS) + PAUSA);
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
