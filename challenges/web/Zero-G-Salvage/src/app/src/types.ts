export type Commodity = {
	ticker: string;
	name: string;
	pricePerTon: number;
	changePct: number;
	volumeTons: number;
};

export type Grade = "Flight-Worthy" | "Reclaimed" | "Cold-Soak" | "Parts Only";

export type Listing = {
	id: string;
	title: string;
	category: string;
	grade: Grade;
	askPrice: number;
	qty: number;
	seller: string;
	origin: string;
	description?: string;
	ownedByYou?: number;
	returnable?: boolean;
	flag?: string;
};

export type Account = {
	credits: number;
	holdings: Record<string, number>;
};

export type MarketStats = {
	tonsCleared: number;
	verifiedHaulers: number;
	volumeCr: number;
};

export type PricePoint = {
	date: string;
	price: number;
};

export type TradeResult = {
	proceeds?: number;
	fee?: number;
	cost?: number;
	credits: number;
	holdings: number;
};

export type VoucherResult = {
	granted: number;
	credits: number;
};

export type Quote = {
	quoteId: string;
	ticker: string;
	qty: number;
	price: number;
	expiresAt: number;
};

export type PurchaseResult = {
	purchased: boolean;
	credits: number;
	item: string;
	flag?: string;
};

export type ReturnResult = {
	returned: boolean;
	credits: number;
	item: string;
};
