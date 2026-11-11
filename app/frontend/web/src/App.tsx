import { useEffect, useState } from "react";
import { Button, Tab, TabList, Text, Tooltip } from "@fluentui/react-components";
import { ArrowResetRegular } from "@fluentui/react-icons";
import { api } from "./api";
import { QueuePage } from "./pages/Queue";
import { CasePage } from "./pages/CaseWorkspace";
import { TracePage } from "./pages/Trace";
import { ProviderPage } from "./pages/Provider";
import { QualityPage } from "./pages/Quality";

export type Route =
  | { page: "queue" }
  | { page: "case"; id: string }
  | { page: "trace"; id: string }
  | { page: "provider" }
  | { page: "quality" };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "case" && parts[1]) {
    return parts[2] === "trace" ? { page: "trace", id: parts[1] } : { page: "case", id: parts[1] };
  }
  if (parts[0] === "provider") return { page: "provider" };
  if (parts[0] === "quality") return { page: "quality" };
  return { page: "queue" };
}

export const go = (path: string) => {
  window.location.hash = path;
};

function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

const NAV = [
  { value: "queue", label: "Reviewer queue", path: "/queue" },
  { value: "provider", label: "Provider portal", path: "/provider" },
  { value: "quality", label: "Quality", path: "/quality" },
];

export function App() {
  const route = useRoute();
  const [epoch, setEpoch] = useState(0);
  const tab = route.page === "case" || route.page === "trace" ? "queue" : route.page;

  const reset = async () => {
    await api.reset();
    setEpoch((n) => n + 1);
    go("/queue");
  };

  return (
    <div className="shell">
      <header className="topbar">
        <Text weight="semibold" size={500} className="brand">
          AutoAuth <span className="muted">· prior authorization</span>
        </Text>
        <TabList
          selectedValue={tab}
          onTabSelect={(_, d) => go(NAV.find((n) => n.value === d.value)!.path)}
        >
          {NAV.map((n) => (
            <Tab key={n.value} value={n.value}>
              {n.label}
            </Tab>
          ))}
        </TabList>
        <span className="spacer" />
        <Text size={200} className="muted">
          Demo data · fictional patients
        </Text>
        <Tooltip content="Restore the seeded demo cases" relationship="label">
          <Button icon={<ArrowResetRegular />} appearance="subtle" onClick={reset}>
            Reset demo
          </Button>
        </Tooltip>
      </header>
      <main key={epoch}>
        {route.page === "queue" && <QueuePage />}
        {route.page === "case" && <CasePage key={route.id} id={route.id} />}
        {route.page === "trace" && <TracePage key={route.id} id={route.id} />}
        {route.page === "provider" && <ProviderPage />}
        {route.page === "quality" && <QualityPage />}
      </main>
    </div>
  );
}
