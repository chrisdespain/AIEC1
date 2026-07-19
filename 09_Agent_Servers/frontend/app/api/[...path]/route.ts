import { initApiPassthrough } from "langgraph-nextjs-api-passthrough";

export const { GET, POST, PUT, PATCH, DELETE, OPTIONS, runtime } =
  initApiPassthrough({
    apiUrl: process.env.LANGGRAPH_API_URL || "http://localhost:2024",
    apiKey: process.env.LANGSMITH_API_KEY,
    disableWarningLog: true,
  });
