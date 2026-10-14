import type { Metadata } from "next";
import { Suspense } from "react";

import styles from "./login.module.css";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "Acceso" };

export default function LoginPage() {
  return (
    <div className={styles.page}>
      <section className={styles.hero} aria-label="DEKEN STUDIO AI">
        <span className={styles.wordmark}>DEKEN STUDIO AI</span>
        <p className={styles.claim}>
          Contenido real de fábrica para <strong>profesionales</strong> de la ventana.
        </p>
        <div>
          <p className={styles.heroLabel}>Grupo Deken · Santiponce, Sevilla</p>
          <p className={styles.heroFooter}>
            Plataforma privada de producción audiovisual, dirección creativa y planificación de
            contenidos. Acceso solo para personal autorizado.
          </p>
        </div>
      </section>
      <main className={styles.panel}>
        <h1>Iniciar sesión</h1>
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
        <p className={styles.note}>
          ¿Sin acceso? Pide a un administrador que cree tu usuario. Las cuentas no se registran
          desde aquí.
        </p>
      </main>
    </div>
  );
}
