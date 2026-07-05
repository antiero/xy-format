import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";
import { applyNativeEmbedClass } from "./lib/embedMode";

applyNativeEmbedClass();

const app = mount(App, {
  target: document.getElementById("app")!,
});

export default app;
