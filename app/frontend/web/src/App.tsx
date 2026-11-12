import { Fragment, useEffect, useState, type ReactElement } from "react";
import {
  Avatar,
  Breadcrumb,
  BreadcrumbButton,
  BreadcrumbDivider,
  BreadcrumbItem,
  Button,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowResetRegular,
  BranchCompareRegular,
  DataBarVerticalRegular,
  DocumentArrowUpRegular,
  LibraryRegular,
  SparkleFilled,
  TaskListSquareLtrRegular,
} from "@fluentui/react-icons";
import { api } from "./api";
import { QueuePage } from "./pages/Queue";
import { CasePage } from "./pages/CaseWorkspace";
import { TracePage } from "./pages/Trace";
import { ProviderPage } from "./pages/Provider";
import { QualityPage } from "./pages/Quality";
import { ParityPage } from "./pages/Parity";
import { IndexesPage } from "./pages/Indexes";

export type Route =
  | { page: "queue" }
  | { page: "case"; id: string }
  | { page: "trace"; id: string }
  | { page: "provider" }
  | { page: "quality" }
  | { page: "parity" }
  | { page: "indexes"; step: IndexStep; caseId?: string };

export type IndexStep = "prior" | "runtime" | "kept";
const INDEX_STEPS: IndexStep[] = ["prior", "runtime", "kept"];

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "case" && parts[1]) {
    return parts[2] === "trace" ? { page: "trace", id: parts[1] } : { page: "case", id: parts[1] };
  }
  if (parts[0] === "provider") return { page: "provider" };
  if (parts[0] === "quality") return { page: "quality" };
  if (parts[0] === "parity") return { page: "parity" };
  if (parts[0] === "indexes") {
    const step = INDEX_STEPS.includes(parts[1] as IndexStep) ? (parts[1] as IndexStep) : "prior";
    return { page: "indexes", step, caseId: step === "runtime" ? parts[2] : undefined };
  }
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

type NavItem = { value: Route["page"]; label: string; path: string; icon: ReactElement };

const NAV: NavItem[] = [
  { value: "queue", label: "Review queue", path: "/queue", icon: <TaskListSquareLtrRegular /> },
  { value: "provider", label: "Send a request", path: "/provider", icon: <DocumentArrowUpRegular /> },
  { value: "indexes", label: "Policy library", path: "/indexes", icon: <LibraryRegular /> },
  { value: "quality", label: "Quality", path: "/quality", icon: <DataBarVerticalRegular /> },
  { value: "parity", label: "Parity", path: "/parity", icon: <BranchCompareRegular /> },
];

/** Breadcrumbs only appear below the top level, where there is somewhere to go back to. */
function crumbs(route: Route): { label: string; path?: string }[] {
  const queue = { label: "Review queue", path: "/queue" };
  switch (route.page) {
    case "case":
      return [queue, { label: route.id }];
    case "trace":
      return [queue, { label: route.id, path: `/case/${route.id}` }, { label: "Agent trace" }];
    default:
      return [];
  }
}

export function App() {
  const route = useRoute();
  const [epoch, setEpoch] = useState(0);
  const section = route.page === "case" || route.page === "trace" ? "queue" : route.page;
  const trail = crumbs(route);

  const reset = async () => {
    await api.reset();
    setEpoch((n) => n + 1);
    go("/queue");
  };

  return (
    <div className="shell">
      <header className="topbar">
        <a className="brand" href="#/queue" aria-label="AutoAuth home">
          <span className="brand-logo" aria-hidden>
            <SparkleFilled />
          </span>
          <span className="brand-text">
            <b>AutoAuth</b>
            <span>on Microsoft Azure</span>
          </span>
        </a>
        <nav className="tabs" aria-label="Main">
          {NAV.map((n) => (
            <a
              key={n.value}
              href={`#${n.path}`}
              className={`tab${section === n.value ? " active" : ""}`}
              aria-current={section === n.value ? "page" : undefined}
              data-nav={n.value}
            >
              <span className="tab-icon">{n.icon}</span>
              <span className="tab-label">{n.label}</span>
            </a>
          ))}
        </nav>
        <span className="spacer" />
        <Tooltip content="Offline demo: fictional patients plus the real prototype cases" relationship="description">
          <span className="demo-chip">✨ Demo mode</span>
        </Tooltip>
        <Tooltip content="Restore the seeded demo cases" relationship="label">
          <Button appearance="subtle" shape="circular" icon={<ArrowResetRegular />} onClick={reset} className="top-btn">
            Reset
          </Button>
        </Tooltip>
        <Tooltip content="J. Reviewer · Contoso Health Plan" relationship="label">
          <Avatar name="J Reviewer" size={32} className="me" />
        </Tooltip>
      </header>
      <main key={epoch}>
        <div className="page">
          {trail.length ? (
            <Breadcrumb aria-label="Breadcrumb" size="small" className="crumbs">
              {trail.map((c, i) => (
                <Fragment key={i}>
                  <BreadcrumbItem>
                    <BreadcrumbButton
                      current={i === trail.length - 1}
                      onClick={c.path && i < trail.length - 1 ? () => go(c.path!) : undefined}
                    >
                      {c.label}
                    </BreadcrumbButton>
                  </BreadcrumbItem>
                  {i < trail.length - 1 ? <BreadcrumbDivider /> : null}
                </Fragment>
              ))}
            </Breadcrumb>
          ) : null}
          {route.page === "queue" && <QueuePage />}
          {route.page === "case" && <CasePage key={route.id} id={route.id} />}
          {route.page === "trace" && <TracePage key={route.id} id={route.id} />}
          {route.page === "provider" && <ProviderPage />}
          {route.page === "quality" && <QualityPage />}
          {route.page === "parity" && <ParityPage />}
          {route.page === "indexes" && <IndexesPage step={route.step} caseId={route.caseId} />}
        </div>
      </main>
    </div>
  );
}
