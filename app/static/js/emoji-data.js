// Emoji offered by the picker, grouped for browsing. Each group lists emoji separated by spaces.
// Only single, widely supported emoji (Unicode 12 or older, no skin tones or joined sequences),
// all accepted by the API's rules for the "emoji" icon kind.
const GROUPS = [
  {
    name: "Activities",
    emojis:
      "🏃 🚶 💃 🕺 🧘 🧗 🏋️ 🚴 🚵 🏊 🏄 🤸 🤾 ⚽ 🏀 🏈 ⚾ 🎾 🏐 🏉 🎱 🏓 🏸 🥊 🥋 🏹 🎣 ⛳ ⛸️ 🎿 🏂 🛹 🏆 🥇 🥈 🥉 🎯 🎳",
  },
  {
    name: "Health",
    emojis:
      "❤️ 🩸 💊 💉 🩺 🩹 🌡️ 🧠 🦷 🦴 👀 💪 🛌 😴 🚿 🛁 🧴 🧼",
  },
  {
    name: "Mood",
    emojis:
      "😀 😃 😄 😁 😊 🙂 😍 🥰 😎 🤩 😐 😑 😕 😟 😢 😭 😡 😤 😰 😱 🤒 🤕 🤢 😷 🥵 🥶",
  },
  {
    name: "Food and drink",
    emojis:
      "🍎 🍌 🍇 🍓 🥑 🥦 🥕 🌽 🍞 🧀 🍳 🥗 🍕 🍔 🍟 🌮 🍣 🍜 🍝 🍪 🍰 🍫 🍩 🍦 ☕ 🍵 🥤 🧃 🥛 💧 🍺 🍷",
  },
  {
    name: "Nature and weather",
    emojis:
      "🐶 🐱 🐴 🐦 🐟 🌱 🌳 🌸 🌻 🍀 🌍 ☀️ ⛅ ☁️ 🌧️ ⚡ ❄️ 🔥 🌈 🌊 🌙 ⭐",
  },
  {
    name: "Home and work",
    emojis:
      "💼 📚 📖 ✏️ 💻 📱 🎧 🎮 🎬 🎨 🎸 🎹 📷 🧹 🧺 🛒 🔧 💡 ⏰ 📅 💰 💳 🏠 🚗 🚌 🚲 ✈️ 🚆 🧳",
  },
  {
    name: "Symbols",
    emojis:
      "✅ ❌ ⚠️ ❓ ❗ ➕ ➖ 🔴 🟠 🟡 🟢 🔵 🟣 🟤 ⚫ ⚪ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 ✨ 🎉 🎁 🔔 📌 🏁 🚩",
  },
];

export const EMOJI_GROUPS = GROUPS.map(({ name, emojis }) => ({ name, emojis: emojis.split(" ") }));
