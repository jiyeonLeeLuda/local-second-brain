import { StatusBar } from "@/components/StatusBar/StatusBar";
import { StudyWorkspace } from "@/components/StudyWorkspace/StudyWorkspace";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.title}>스터디 Q&amp;A</h1>
        <p className={styles.subtitle}>내 스터디 노트에서 근거를 찾아 답합니다. 원본은 내가 쓴 MD 파일입니다.</p>
      </header>

      <main className={styles.main}>
        <StudyWorkspace />
      </main>

      <StatusBar />
    </div>
  );
}
