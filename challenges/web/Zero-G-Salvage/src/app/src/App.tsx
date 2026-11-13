import { Route, Routes } from "react-router-dom";
import CommodityDetailPage from "./pages/CommodityDetailPage";
import DisclosuresPage from "./pages/DisclosuresPage";
import ListingsPage from "./pages/ListingsPage";
import MarketPage from "./pages/MarketPage";
import PortfolioPage from "./pages/PortfolioPage";
import ReturnPolicyPage from "./pages/ReturnPolicyPage";

function App() {
	return (
		<Routes>
			<Route path="/" element={<MarketPage />} />
			<Route path="/commodity/:ticker" element={<CommodityDetailPage />} />
			<Route path="/listings" element={<ListingsPage />} />
			<Route path="/portfolio" element={<PortfolioPage />} />
			<Route path="/disclosures" element={<DisclosuresPage />} />
			<Route path="/return-policy" element={<ReturnPolicyPage />} />
		</Routes>
	);
}

export default App;
