"use client";

import { Film } from "lucide-react";
import { useState, type PointerEvent } from "react";

import styles from "./library.module.css";

/** Proporción de la caja de miniatura de la galería. */
const BOX_ASPECT = 16 / 9;

/**
 * Póster del vídeo y, al pasar el puntero, la tira de fotogramas para "hojear" el clip.
 * Nunca se deforma: póster con object-fit: contain y tira recortada a un fotograma con
 * la proporción real del vídeo.
 */
export function Thumb({
  posterUrl,
  stripUrl,
  stripFrames,
  width,
  height,
  label,
}: {
  posterUrl: string | null | undefined;
  stripUrl: string | null | undefined;
  stripFrames: number | null | undefined;
  width: number | null | undefined;
  height: number | null | undefined;
  label: string;
}) {
  const [frame, setFrame] = useState<number | null>(null);
  const frames = stripFrames ?? 0;
  const aspect = width && height ? width / height : BOX_ASPECT;
  // Rectángulo del fotograma dentro de la caja (en % de la caja), centrado.
  const fw = aspect >= BOX_ASPECT ? 100 : (aspect / BOX_ASPECT) * 100;
  const fh = aspect >= BOX_ASPECT ? (BOX_ASPECT / aspect) * 100 : 100;

  function onMove(event: PointerEvent<HTMLDivElement>) {
    if (!stripUrl || frames < 2) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.min(0.999, Math.max(0, (event.clientX - rect.left) / rect.width));
    setFrame(Math.floor(x * frames));
  }

  return (
    <div className={styles.thumb} onPointerMove={onMove} onPointerLeave={() => setFrame(null)}>
      {posterUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- URL firmada del almacenamiento
        <img className={styles.poster} src={posterUrl} alt={label} loading="lazy" draggable={false} />
      ) : (
        <div className={styles.thumbEmpty} aria-hidden="true">
          <Film size={28} />
        </div>
      )}
      {stripUrl && frame !== null ? (
        <div
          className={styles.stripClip}
          style={{ width: `${fw}%`, height: `${fh}%`, left: `${(100 - fw) / 2}%`, top: `${(100 - fh) / 2}%` }}
          aria-hidden="true"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- URL firmada del almacenamiento */}
          <img
            className={styles.strip}
            src={stripUrl}
            alt=""
            draggable={false}
            style={{ width: `${frames * 100}%`, transform: `translateX(-${(frame / frames) * 100}%)` }}
          />
          <span className={styles.scrubBar} style={{ width: `${((frame + 1) / frames) * 100}%` }} />
        </div>
      ) : null}
    </div>
  );
}
