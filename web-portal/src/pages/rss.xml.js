import { getCollection } from 'astro:content';

export async function GET(context) {
  const posts = await getCollection('blog');
  
  // Sort posts by date descending
  const sortedPosts = posts.sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf());
  
  const siteUrl = context.site || 'https://aihaberler.web.app';
  
  const items = sortedPosts.map(post => {
    const postUrl = new URL(`/blog/${post.id}`, siteUrl).toString();
    return `
    <item>
      <title><![CDATA[${post.data.title}]]></title>
      <link>${postUrl}</link>
      <guid isPermaLink="true">${postUrl}</guid>
      <description><![CDATA[${post.data.description}]]></description>
      <pubDate>${post.data.pubDate.toUTCString()}</pubDate>
      <category><![CDATA[${post.data.category}]]></category>
    </item>`;
  }).join('');

  const feed = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
  xmlns:content="http://purl.org/rss/1.0/modules/content/" 
  xmlns:dc="http://purl.org/dc/elements/1.1/" 
  xmlns:atom="http://www.w3.org/2005/Atom" 
  xmlns:sy="http://purl.org/rss/1.0/modules/syndication/">
  <channel>
    <title>AIHABERLER</title>
    <link>${siteUrl}</link>
    <description>Endüstriyel otomasyon, PLC yazılımları, endüstriyel arıza giderme, pano tasarımı, elektrik ve donanım pratik tamir rehberleri.</description>
    <language>tr</language>
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
    <atom:link href="${new URL('rss.xml', siteUrl)}" rel="self" type="application/rss+xml" />
    ${items}
  </channel>
</rss>`;

  return new Response(feed, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600'
    }
  });
}
