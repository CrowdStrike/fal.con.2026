import React from "react";
import { HashRouter, Routes, Route, Outlet } from "react-router-dom";
import {
  useFalconApiContext,
  FalconApiContext,
} from "./contexts/falcon-api-context";
import { Home } from "./routes/home";
import { About } from "./routes/about";
import ReactDOM from "react-dom/client";
import { TabNavigation } from "./components/navigation";

function Root() {
  return (
    <Routes>
      <Route
        element={
          <TabNavigation>
            <Outlet />
          </TabNavigation>
        }
      >
        <Route index path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
      </Route>
    </Routes>
  );
}

function App() {
  const { falcon, navigation, isInitialized } = useFalconApiContext();

  if (!isInitialized) {
    return null;
  }

  return (
    <React.StrictMode>
      <FalconApiContext.Provider value={{ falcon, navigation, isInitialized }}>
        <HashRouter>
          <Root />
        </HashRouter>
      </FalconApiContext.Provider>
    </React.StrictMode>
  );
}

const domContainer = document.querySelector("#app");
const root = ReactDOM.createRoot(domContainer);

root.render(<App />);
