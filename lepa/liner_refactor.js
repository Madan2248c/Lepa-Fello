const fs = require('fs');
const path = require('path');

const filesToUpdate = [
    'app/layout.tsx',
    'components/Sidebar.tsx',
    'components/Header.tsx',
    'app/accounts/page.tsx',
    'app/analyze/page.tsx',
    'app/history/page.tsx',
    'app/settings/page.tsx',
    'components/PipelineView.tsx',
    'app/globals.css'
];

const colorMap = [
    // Backgrounds
    { from: /bg-\[#0E0F11\]/g, to: 'bg-[#0B120F]' },
    { from: /bg-\[#0a0a0b\]/g, to: 'bg-[#0B120F]' },
    { from: /bg-\[#0A0A0B\]/g, to: 'bg-[#0B120F]' },
    { from: /bg-\[#18191B\]/g, to: 'bg-[#15231D]' },
    { from: /bg-\[#27282B\]/g, to: 'bg-[#20342B]' },

    // Opacity Backgrounds
    { from: /bg-\[#0E0F11\]\/50/g, to: 'bg-[#0B120F]/50' },
    { from: /bg-\[#0E0F11\]\/40/g, to: 'bg-[#0B120F]/40' },
    { from: /bg-\[#18191B\]\/30/g, to: 'bg-[#15231D]/30' },
    { from: /bg-\[#18191B\]\/50/g, to: 'bg-[#15231D]/50' },
    { from: /bg-white\/5/g, to: 'bg-[#20342B]/40' },

    // Borders
    { from: /border-\[#27282B\]/g, to: 'border-[#20342B]' },

    // Text
    { from: /text-\[#F2F4F8\]/g, to: 'text-[#F4F5F0]' },
    { from: /text-\[#D0D6E0\]/g, to: 'text-[#E0E3D8]' },
    { from: /text-\[#8A8F98\]/g, to: 'text-[#9CA8A3]' },

    // Accents (Indigo to Lime Green)
    { from: /bg-\[#5e6ad2\]/g, to: 'bg-[#B2FF33] text-[#0B120F]' },
    { from: /hover:bg-\[#6c79e8\]/g, to: 'hover:bg-[#9DE02A]' },
    { from: /text-\[#8b9ff7\]/g, to: 'text-[#B2FF33]' },
    { from: /text-\[#5e6ad2\]/g, to: 'text-[#B2FF33]' },
    { from: /border-\[#5e6ad2\]/g, to: 'border-[#B2FF33]' },
    { from: /ring-\[#5e6ad2\]/g, to: 'ring-[#B2FF33]' },
    { from: /shadow-\[#5e6ad2\]/g, to: 'shadow-[#B2FF33]' },
    { from: /from-\[#5e6ad2\]/g, to: 'from-[#B2FF33]' },

    // Accents (Purple to Orange)
    { from: /to-\[#9278E2\]/g, to: 'to-[#FF7B40]' },
    { from: /bg-\[#9278E2\]/g, to: 'bg-[#FF7B40] text-white' },
    { from: /hover:bg-\[#a68ff0\]/g, to: 'hover:bg-[#E56E39]' },
    { from: /ring-\[#9278E2\]/g, to: 'ring-[#FF7B40]' }
];

for (const file of filesToUpdate) {
    const filePath = path.join(process.cwd(), file);
    if (fs.existsSync(filePath)) {
        let content = fs.readFileSync(filePath, 'utf8');

        for (const rule of colorMap) {
            content = content.replace(rule.from, rule.to);
        }

        // Convert to dotted borders to match Liner's "precision" design language
        content = content.replace(/border-b border-white\/5/g, 'border-b border-dashed border-[#20342B]');
        content = content.replace(/border-b border-\[#20342B\]/g, 'border-b border-dashed border-[#20342B]');
        content = content.replace(/border-r border-white\/5/g, 'border-r border-dashed border-[#20342B]');
        content = content.replace(/border-t border-white\/5/g, 'border-t border-dashed border-[#20342B]');
        content = content.replace(/border-t border-\[#20342B\]/g, 'border-t border-dashed border-[#20342B]');
        content = content.replace(/border border-\[#20342B\]/g, 'border border-dashed border-[#20342B]');

        // Ensure serif font is used in text
        content = content.replace(/font-sans/g, 'font-serif');

        fs.writeFileSync(filePath, content);
        console.log(`Updated ${file}`);
    }
}
