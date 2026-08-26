import React  from "react";
import { useLocation } from "react-router-dom";
import { Link } from './link';
import {
  SlTab,
  SlTabGroup,
  SlTabPanel,
} from "@shoelace-style/shoelace/dist/react";

function TabNavigation({ children }) {
  const location = useLocation();
  
  return (
    <SlTabGroup>
      <SlTab active={location.pathname === "/"} slot="nav" panel="home">
        <Link className="no-underline" to="/">
          Home
        </Link>
      </SlTab>
      <SlTab active={location.pathname === "/about"} slot="nav" panel="about">
        <Link className="no-underline" to="/about">
          About
        </Link>
      </SlTab>
      <SlTabPanel name="home">{children}</SlTabPanel>
      <SlTabPanel name="about">{children}</SlTabPanel>
    </SlTabGroup>
  );
}

export { TabNavigation };