"use client";

import { useEffect, useState, type RefObject } from "react";

import styles from "./library.module.css";

/**
 * Forma de onda (picos absolutos 0–1 calculados en la ingesta) sincronizada con el
 * reproductor: muestra la posición y permite saltar a un punto con clic o teclado.
 */
export function Waveform({
  peaks,
  duration,
  video,
  onSeek,
}: {
  peaks: number[];
  duration: number;
  /** Reproductor cuya posición se muestra (solo lectura). */
  video: RefObject<HTMLVideoElement | null>;
  onSeek: (seconds: number) => void;
}) {
  const [position, setPosition] = useState(0);

  useEffect(() => {
    const el = video.current;
    if (!el) return;
    let frame = 0;
    const tick = () => {
      setPosition(el.currentTime);
      if (!el.paused) frame = requestAnimationFrame(tick);
    };
    const onPlay = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(tick);
    };
    const sync = () => setPosition(el.currentTime);
    el.addEventListener("play", onPlay);
    el.addEventListener("seeked", sync);
    el.addEventListener("timeupdate", sync);
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener("play", onPlay);
      el.removeEventListener("seeked", sync);
      el.removeEventListener("timeupdate", sync);
    };
  }, [video]);

  const seek = (fraction: number) => {
    if (!duration) return;
    onSeek(Math.max(0, Math.min(duration, fraction * duration)));
  };
  const fraction = duration ? Math.min(1, position / duration) : 0;
  const n = Math.max(1, peaks.length);

  return (
    <div
      className={styles.waveform}
      role="slider"
      tabIndex={0}
      aria-label="Forma de onda del audio (posición de reproducción)"
      aria-valuemin={0}
      aria-valuemax={Math.round(duration)}
      aria-valuenow={Math.round(position)}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        seek((e.clientX - rect.left) / rect.width);
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight") seek(fraction + 5 / duration);
        if (e.key === "ArrowLeft") seek(fraction - 5 / duration);
      }}
    >
      <svg viewBox={`0 0 ${n} 100`} preserveAspectRatio="none" aria-hidden="true">
        {peaks.map((p, i) => {
          const h = Math.max(1, p * 96);
          return (
            <rect
              key={i}
              x={i}
              y={50 - h / 2}
              width={0.8}
              height={h}
              className={i / n <= fraction ? styles.wavePlayed : styles.wave}
            />
          );
        })}
      </svg>
      <span className={styles.playhead} style={{ left: `${fraction * 100}%` }} />
    </div>
  );
}
