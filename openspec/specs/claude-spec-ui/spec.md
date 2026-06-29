# Claude UI & QoL Polish Spec

Please implement the following frontend UI improvements and Quality of Life (QoL) features in the React application:

## 1. UI Resizing and Polishing
- **Tower Menu Size & Scrolling**: The tower combat menu is too large for base zoom levels on typical screens, forcing the user to zoom out the browser to see the whole fight. If zoomed in, scrolling down snaps back up when an action occurs. Please make the UI sizing dynamic/responsive to the monitor resolution.
- **Custom Scrollbar**: The default browser scrollbar on the right side is ugly. Please implement a sleek, custom scrollbar styling globally or for main scrollable containers.
- **Notification Sizing**: In-game notifications (e.g., "summoning full") currently sit all the way at the bottom of the screen and get cut off or missed. Ensure notifications are dynamically sized, positioned properly (e.g., top-right or clearly visible bottom-center), and responsive to monitor size.
- **Explore UI Bug**: In the exploration option UI, the user can currently click all over the place (effectively selecting equivalent to 9 boxes). Fix it so they can only truly select the intended 3 options, ensuring the visual UI matches the state limits.

## 2. Heroes Tab & Vault Redesign
- **Heroes Tab**: Currently, hero portraits stretch very long as a hero gets more accomplished (stats, items, etc.). Limit the default height/info of the portraits in the list view, and only expand/show everything when the user clicks on a hero to highlight them.
- **Vault UI**: The vault is currently obnoxious and overwhelming. Redesign it so:
  - It is easy to tell what an item is.
  - It is easy to tell what is "good".
  - It is easy to tell what is equipped vs. unequipped.
  - Differences between items are clear.
  - Add the ability to equip an item directly from the Vault menu.

## 3. Inventory Filters & Quick Actions
- **Non-equipped Filter**: Add a filter button/dropdown in the inventory to only show items that are NOT currently equipped by anyone.
- **Auto Equip / Unequip**: Add an "Auto Equip" button that equips the best available unequipped items to a hero. Also add an "Unequip All" button to easily strip a hero's items.
- **Hero/Team Comparison**: Add a comparison feature in the UI so the user can easily compare Team vs. Team and Hero vs. Hero to decide who they want to bring to combat.

## 4. Combat UI 
- **2x Speed**: Add a 2x combat speed toggle button.
- **Active Skills Visual Tell**: Currently, active skills just show up as text in the combat log. Please add a visual tell on the frontend. This should be an animation above the hero portrait (or visually on the hero themselves) when their active skill triggers. 
- **Mana UI (CRITICAL)**: Mana is not displayed on the heroes in the frontend. It needs to be everywhere:
  - Show Max Mana when looking at a hero's stat sheet.
  - Show a Mana bar (or mana points) during combat fights.
  - Visually deplete the frontend mana bar when an active skill is cast.
