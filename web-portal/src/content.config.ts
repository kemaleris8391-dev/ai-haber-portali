import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
	loader: glob({ pattern: '**/[^_]*.md', base: "./src/content/blog" }),
	schema: z.object({
		title: z.string(),
		description: z.string(),
		pubDate: z.coerce.date(),
		heroImage: z.string().optional(),
		category: z.string().default('genel'),
		tags: z.array(z.string()).default([]),
		sourceName: z.string().optional(),
		sourceUrl: z.string().optional(),
		dateModified: z.coerce.date().optional(),
		author: z.string().optional(),
	}),
});

export const collections = { blog };
